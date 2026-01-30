# Design Doc: Multi-Trial Benchmarking & Statistical Analysis

**Status:** Draft
**Date:** 2026-01-30
**Author:** Gemini CLI Agent

## 1. Problem Statement
Current benchmarking runs execute each test case exactly once per generator. While this provides a snapshot of performance, it fails to capture the **variance** inherent in LLM generation. A single "Pass" or "Fail" might be a statistical outlier (lucky guess or transient error).

To accurately compare generators (e.g., "Is Vector Search *statistically significantly* better than Docs?"), we need to establish a **distribution of accuracies** for each case and generator.

## 2. Goals
1.  **Reliability:** Compute Mean Pass Rate and Standard Deviation/Confidence Intervals for each benchmark case.
2.  **Consistency:** Quantify the "flakiness" of a generator (e.g., "Passes 80% of the time" vs "Passes 100%").
3.  **Visualization:** Visualize performance distributions in the Viewer (Box plots, Error bars).
4.  **Efficiency:** Run trials in parallel where possible, respecting concurrency limits.

## 3. Execution Strategy

### Option A: Breadth-First (Run Suite N times)
Execute the entire benchmark suite N times sequentially or in parallel.
*   *Pros:* Simple to implement (just call the script N times).
*   *Cons:* Hard to correlate results; cache thrashing (setup/teardown repeated).

### Option B: Depth-First (Case-Level Trials) - **RECOMMENDED**
For each case, spawn N independent tasks.
*   *Pros:* Better resource locality (keep generator warm); easier aggregation in the orchestrator; allows for "Adaptive Sampling" (stop early if converged).
*   *Cons:* Requires modifying the orchestrator core loop.

We will proceed with **Option B** (Task Expansion).

## 4. Implementation Design

### 4.1 Orchestrator Updates (`benchmarks/benchmark_orchestrator.py`)

Add a `trials: int` argument to `run_benchmarks`.
Instead of creating 1 task per case, we create `trials` tasks per case.

**Pseudocode:**

```python
async def run_benchmarks(
    suites: List[str], 
    generators: List[AnswerGenerator], 
    trials: int = 1,
    ...
) -> List[BenchmarkRunResult]:

    tasks = []
    
    for gen in generators:
        for suite in suites:
            cases = load_suite(suite)
            
            for case in cases:
                # Create N independent trials for this case
                for trial_idx in range(trials):
                    
                    # Create a "Trial ID" to track this specific execution
                    # e.g., "case_id::gen_name::trial_0"
                    
                    task = _run_single_benchmark(
                        case=case,
                        generator=gen,
                        trial_index=trial_idx,  # NEW: Pass trial index
                        ...
                    )
                    tasks.append(task)

    # Execute all tasks (concurrency limit applies globally)
    results = await limited_gather(tasks, limit=MAX_CONCURRENCY)
    
    return results
```

### 4.2 Data Model Updates (`benchmarks/data_models.py`)

We need to track which trial a result belongs to. We can add metadata to `BenchmarkRunResult`.

```python
class BenchmarkRunResult(BaseModel):
    # ... existing fields ...
    
    trial_index: int = Field(0, description="The index of this trial (0-based) in a multi-trial run.")
    total_trials: int = Field(1, description="Total number of trials requested for this run.")
    
    # We do NOT need to nest results. A flat list of results where 
    # (id, answer_generator) is the grouping key is sufficient and easier for Pandas.
```

### 4.3 Analysis & Reporting (`benchmarks/analysis.py`)

We need a new aggregation layer that groups by `(answer_generator, benchmark_id)`.

**Metrics to Calculate:**
1.  **Case Stability:** `Pass Rate = (Passed Trials / Total Trials)` for a single case.
2.  **Generator Variance:** Standard Deviation of Pass Rates across the suite.
3.  **Confidence Intervals:** 95% CI for the Overall Pass Rate.

**Pseudocode (Aggregation):**

```python
def aggregate_multi_trial_results(df: pd.DataFrame):
    # Group by Generator and Case ID
    case_stats = df.groupby(["answer_generator", "suite", "id"]).agg(
        pass_count=("result", "sum"),
        total_trials=("result", "count"),
        avg_latency=("latency", "mean"),
        latency_std=("latency", "std")
    )
    
    case_stats["pass_rate"] = case_stats["pass_count"] / case_stats["total_trials"]
    
    # Identify Flaky Cases
    # Flaky = 0% < pass_rate < 100%
    case_stats["is_flaky"] = case_stats["pass_rate"].between(0.01, 0.99)
    
    return case_stats

def print_statistical_summary(case_stats):
    # Aggregate to Generator level
    gen_stats = case_stats.groupby("answer_generator").agg(
        mean_pass_rate=("pass_rate", "mean"),
        std_pass_rate=("pass_rate", "std"), # Variance between cases
        flaky_case_count=("is_flaky", "sum")
    )
    
    # Display table with Error Bars (Mean ± StdDev)
    print(gen_stats)
```

### 4.4 Viewer Updates (`tools/viewer/view_benchmarks.py`)

The Viewer currently assumes 1 Row = 1 Case. We need to shift to **1 Row = 1 Case Distribution**.

**UI Changes:**
1.  **Main Table:**
    *   Change "Status" column from icon (✅/❌) to a **Progress Bar** or **Sparkline** representing the Pass Rate (e.g., "80% [████░]").
    *   Add a "Stability" column (Stable vs Flaky).

2.  **Case Detail View:**
    *   Instead of showing "Attempt 1..N" (which currently means retries for a *single* result), we need a higher-level grouping.
    *   **Tabs:** "Trial 1", "Trial 2", "Trial 3".
    *   Inside "Trial X", we show the standard Attempt/Retry view.
    *   **Distribution Plot:** A histogram of Latency or Token Usage across trials.

**Pseudocode (Viewer Data Prep):**

```python
def load_and_group_trials(results):
    # Group flat list of results by Case ID
    grouped = defaultdict(list)
    for r in results:
        key = (r.answer_generator, r.id)
        grouped[key].append(r)
        
    return grouped

def render_case_row(trials):
    pass_rate = sum(t.result for t in trials) / len(trials)
    
    if pass_rate == 1.0:
        icon = "✅ (100%)"
    elif pass_rate == 0.0:
        icon = "❌ (0%)"
    else:
        icon = f"⚠️ ({pass_rate:.0%})"
        
    st.write(icon)
```

## 5. Storage Considerations
Running 5 trials for 100 cases = 500 records.
`results.json` size will grow linearly.
*   Current size: ~500KB for 100 cases.
*   5x size: ~2.5MB.
*   **Verdict:** Standard JSON is still fine. No need for SQLite yet.

## 6. CLI Arguments
Update `run_benchmarks.sh` and `run_benchmarks.py`:

```bash
# Run 5 trials per case
./tools/cli/run_benchmarks.sh --trials 5 ...
```

## 7. Future Work: Adaptive Sampling
Instead of fixed N trials, implement **Sequential Probability Ratio Test (SPRT)** or simple convergence checking (like we did for `retrieval_dataset_generation`).
*   Run 3 trials.
*   If all Pass, stop (assume 100%).
*   If mixed, run up to 10 trials to estimate true rate.

## 8. Summary of Tasks
1.  [ ] Add `trials` arg to `run_benchmarks.py`.
2.  [ ] Update `benchmark_orchestrator.py` to loop N times/create N tasks.
3.  [ ] Add `trial_index` to `BenchmarkRunResult`.
4.  [ ] Update `analysis.py` to aggregate by Case ID before summarizing.
5.  [ ] Update `view_benchmarks.py` to handle list-of-results per case.
