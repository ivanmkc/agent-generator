# Guide: Optimizing Agent Architectures

This guide outlines a systematic approach to tuning and refining AI agents. Use this methodology to move from a baseline prototype to a high-performance, cost-effective solution.

## 1. The Goal: Pareto-Optimality

Your objective is to balance two competing metrics. You want the highest possible **Competency** (Pass Rate) with the lowest possible **Token Cost**.

**Target Benchmarks:**
*   **Efficiency:** < 15k tokens per turn.
*   **Competency:** > 50% Pass Rate on the `fix_errors` suite.
*   **Robustness:** Zero reliance on pre-injected knowledge (Zero-Knowledge Architecture).

## 2. The Zero-Knowledge Rule (Mandatory)

To ensure agents are truly general-purpose and capable of working on arbitrary libraries, you MUST adhere to this protocol:

*   **No Code in Prompts:** Never include library-specific API signatures, class definitions, or implementation snippets (e.g., ADK or Pydantic internals) in the system instructions or user prompts.
*   **No Pre-Fetched Context:** Do not "inject" documentation into the prompt before the turn starts.
*   **Discovery via Tools Only:** Instructions must tell the agent *how to find* information (e.g., "Use discovery tools to find the required classes"), not provide the information itself.
*   **Arbitrary Library Support:** The agent's architecture should be agnostic to the target library. It should treat ADK just as it would treat any other third-party package it encounters for the first time.

## 3. The Search Space (The "Knobs")

Think of your agent as a system with four adjustable components.

### Step 0: Iterative Benchmark Strategy

**MANDATORY: Always use `benchmark_run.sh`.**
To ensure consistent environment variables and path configuration, you MUST use the shell script as the entry point for all tests. Do not run python scripts directly.

```bash
# Correct Usage
./benchmark_run.sh run_experiment.py

# Incorrect Usage
python run_experiment.py
```

1.  **Start Small (Debug Suite):**
    Use the `debug` suite to catch basic errors quickly.
    ```bash
    ./benchmark_run.sh notebooks/run_benchmarks.py --suite-filter "debug" --generator-filter "MY_AGENT"
    ```
2.  **Scale Up (Fix Errors):**
    Once the debug suite passes, run the comprehensive `fix_errors` suite.
    ```bash
    ./benchmark_run.sh notebooks/run_benchmarks.py --suite-filter "fix_errors" --generator-filter "MY_AGENT"
    ```
3.  **Full Evaluation (All Suites):**
    Finally, run all suites to check for regression on other tasks.
    ```bash
    ./benchmark_run.sh notebooks/run_benchmarks.py --generator-filter "MY_AGENT"
    ```

### Step 0.5: Flagging Bad Benchmarks
In your debugging process, if you encounter **persistent pesky cases** that fail across multiple agent architectures despite correct reasoning, this indicates a potential issue with the question itself.

**Tooling:**
Use the historical analysis script to pinpoint these cases:
```bash
python tools/analysis/analyze_historical_pass_rates.py
```
Focus on cases with a low **Weighted Pass Rate**. This metric prioritizes recent runs while accounting for long-term failure patterns.

*   **Action:** Verify the ground truth manually for these low-pass-rate cases.
*   **Instruction:** If the benchmark question is ambiguous or the ground truth is outdated/incorrect, flag it in your experiment report and recommend a fix to the benchmark definition file.

### A. Topology (Flow Control)
*Where to look: `benchmarks/answer_generators/`*
*   **Single-Agent ReAct:** *Default Choice.* One loop, one context.
    *   *Implementation:* See `ADK_REACT` in `adk_agents.py`.
*   **Markovian Chain:** *Efficiency Choice.* Specialized steps (Plan -> Code) with isolated state.
    *   *Implementation:* See `SequentialAgent` pattern (if available) or split logic into multiple `LlmAgent` calls.
*   **Hierarchical:** *Complexity Choice.* Manager delegating to workers.
    *   *Implementation:* Requires a router agent that calls other agents as tools.

### B. Discovery Strategy (Information Retrieval)
*Where to look: `tools/` and `benchmarks/config.py`*
*   **Abstracted Inspection:** *Recommended.* Uses `get_module_help` / `read_definitions`.
    *   *How:* Ensure your agent has these tools in `tools_config`.
*   **Naive Search:** *Avoid.* `grep`, `find`.
*   **Context Injection:** *Avoid.* Hardcoding text into `system_instruction`.

### C. Memory Model (Context Management)
*Where to look: Agent Class Definition*
*   **Windowed/Summary:** *Recommended.*
    *   *How:* Use `include_contents='summary'` or implement a `summarize_state()` step.
*   **Isolated:**
    *   *How:* Use `include_contents='none'` and pass state explicitly via prompt arguments.
*   **Full History:**
    *   *How:* Default behavior (`include_contents='all'`).

## 3. Implementation Workflow

### Step A: Create Your Variant
**Rule of Thumb: Never modify a stable agent.** Always create a new variant when testing a hypothesis so you have a baseline to compare against.

1.  Navigate to `benchmarks/answer_generators/`.
2.  **Create a New Class:** Do not edit `ADK_REACT`. Subclass it or create a new class (e.g., `ADK_REACT_V2` or `ADK_STATISTICAL`).
3.  Implement the `AnswerGenerator` interface.
4.  **Register** your new agent key in `benchmarks/benchmark_candidates.py`.

### Step B: Run the Experiment (Latest Only)
To minimize latency and token consumption, **DO NOT** run historical baselines or previous versions alongside your current variant. Only evaluate the specific variant you are currently testing.

```bash
# Target ONLY the latest variant (e.g., V14)
bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V14"
```

**Technical Tip:** The `--generator-filter` uses substring matching. Ensure your name is specific enough to avoid accidental matches (e.g., using `V1` might match `V10`, `V11`, etc., whereas `V14` is precise).

### Step C: Analyze Traces (Debugging)
If the agent fails or uses too many tokens, you need to see *why*. Use the built-in debugging tool to inspect the interaction.

1.  **List failed cases** in your latest run:
    ```bash
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --list-cases
    ```
2.  **Inspect a specific case** by its unique ID (e.g., `suite:slug`):
    ```bash
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --case "api_understanding:what_is_the_foundational_class_for_all_agents_in_t"
    ```
3.  **Key indicators in the trace:**
    *   **Looping:** Is it calling the same tool repeatedly? (Fix: Add history/memory).
    *   **Hallucination:** Is it inventing tool arguments or import paths? (Fix: mandate `search_files` verification).
    *   **Token Bloat:** Is the prompt huge? (Fix: Switch Discovery Strategy).

## 4. The Optimization Cycle (Hill-Climbing)

1.  **Establish Baseline:** Start with `ADK_REACT` (or your best current candidate).
2.  **Measure:** Run `fix_errors` suite.
    ```bash
    bash notebooks/run_benchmarks.sh --suite-filter "fix_errors"
    ```
3.  **Identify Bottleneck:**
    *   *High Tokens?* → Mutate **Discovery** or **Memory**.
    *   *Logic Errors?* → Mutate **Topology**.
4.  **Mutate ONE Variable:** Change code in your agent class.
6.  **Document & Commit:**
    *   **Standardized Location:** Create a new entry in `ai_instructions/experiments/` using the standard template (`ai_instructions/experiments/TEMPLATE.md`).
    *   **Naming Convention:** `ai_instructions/experiments/exp_NN_[name].md` (e.g., `exp_22_statistical_v2.md`).
    *   **Log the details:** Note the action, the result, and *why* it happened (referencing your trace analysis).
    *   **Keep the history:** We learn more from recorded failures than from unrecorded successes.
    *   **Commit:** Once verified, commit the new agent class and the updated report.

### Stop Conditions (When to Ship)
Stop optimizing and "ship" the agent when:
*   **Pass Rate > 50%:** The agent solves the majority of `fix_errors` cases.
*   **Tokens < 15k/turn:** The agent is cost-effective for production.
*   **Zero Hallucinations:** The agent does not invent APIs or import paths (verified via trace analysis).
*   **Diminishing Returns:** Modifying variables yields < 1% improvement for 3 consecutive iterations.

## 5. Historical Context & Data (The "Why")

Before starting a new experiment, review the detailed post-mortems of past failures to avoid repeating them.

*   **Token Reduction Journey:** See `ai_instructions/experiments/agent_optimization/adk_agent_debugging_report.md` for the full phase-by-phase log of experiments 1-15.
*   **Structured vs. Baseline Analysis:** See `ai_instructions/experiments/agent_optimization/structured_vs_baseline_report.md` for a comparison of MAS (Multi-Agent Systems) vs. Single-Agent performance.
*   **Tool Calling Optimization:** See `ai_instructions/experiments/agent_optimization/fix_report_tool_calling.md` for insights on how tool definition changes impacted pass rates.
*   **Structured Workflow Integration:** See `ai_instructions/experiments/agent_optimization/structured_workflow_report.md` for details on workspace isolation and structured outputs.
*   **Progressive Debugging Log:** See `ai_instructions/experiments/agent_optimization/report.md` for early architectural pivots.

## 6. The Toolbelt: Debugging & Analysis Resources

Use these tools to diagnose failures and validate your architecture.

### A. Core Debugging Tool (`tools/debugging.py`)
*   **Purpose:** The primary surgical tool for inspecting agent behavior.
*   **Usage:**
    ```bash
    # List failed cases in a run
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --list-cases

    # Deep dive into a specific case (shows thoughts, tool args, tool outputs)
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --case "api_understanding:identifier_for_case"
    ```

### B. Benchmark Viewer (`tools/benchmark_viewer.py`)
*   **Purpose:** A TUI (Text User Interface) for browsing results across multiple runs.
*   **Usage:**
    ```bash
    python tools/benchmark_viewer.py
    ```

### C. Analyzed Logs (`log_analysis.md`)
*   **Purpose:** High-level summary of a run, generated automatically in the run directory.
*   **Contains:** Pass rates, error categories, and token usage statistics.
*   **Location:** `benchmark_runs/<timestamp>/log_analysis.md`

### D. Validation & Integrity Tests
Use these to verify that the *problem* is with your agent, not the *framework*.

*   **`benchmarks/tests/verification/check_mc_leaks.py`**
    *   **Purpose:** Uses an LLM to check if multiple-choice questions "leak" their answers in the code snippet. Run this if your agent is getting 100% on MCQs too easily.
    *   **Usage:** `env/bin/python benchmarks/tests/verification/check_mc_leaks.py`

*   **`benchmarks/tests/integration/test_unified_generators.py`**
    *   **Purpose:** Runs generators in isolation (low concurrency). If the main benchmark run fails with infrastructure errors (Podman crashes, timeouts), use this to verify the agent's logic is sound.
    *   **Usage:** `python -m pytest benchmarks/tests/integration/test_unified_generators.py`

*   **`benchmarks/tests/verification/test_verify_fix_errors.py`**
    *   **Purpose:** Meta-test that verifies the *quality* of the `fix_error` benchmarks themselves. It checks if the "unfixed" code leaks the solution and if the tests actually verify the failure conditions.
    *   **Usage:** `pytest benchmarks/tests/verification/test_verify_fix_errors.py`

### E. Useful Python Modules for Ad-Hoc Analysis
When inspecting code or writing new tools, leverage these standard libraries:
*   `ast`: For parsing Python code structure (used in `AdkTools.read_definitions`).
*   `inspect`: For runtime introspection of objects and signatures.
*   `pydantic`: Essential for validating agent configuration and tool schemas.
*   `json` & `yaml`: For parsing trace logs and configuration files.

### F. Templates
*   **Experiment Report:** `ai_instructions/experiments/TEMPLATE.md`
    *   Use this for every new agent variant or major test run.

## 7. Deep Dive: Trace Analysis Methodology

Mastering trace analysis is the difference between guessing and solving. Here is how to read the output of `tools/debugging.py`.

### A. Anatomy of a Trace Entry
The logs are a chronological stream of events. Focus on the interplay between three roles:
*   **[USER]:** The system prompt or environment feedback (e.g., `stdout` from a command).
    *   *What to watch:* Is the environment returning errors? Is the context too long (truncated)?
*   **[MODEL THOUGHT]:** The agent's internal monologue.
    *   *What to watch:* Does the reasoning match the action? Is it ignoring previous errors?
*   **[TOOL CALL]:** The action the agent takes.
    *   *What to watch:* Are the arguments correct? Is it calling the right tool?

### B. Common Failure Patterns

#### 1. The "Blind Loop"
*   **Symptom:** The agent calls the same tool with the same arguments 3+ times in a row.
*   **Cause:** It's not seeing the output (Memory issue) or the output is unhelpful, and it refuses to try a different strategy.
*   **Fix:** Ensure `include_contents='default'` (or summary) is set. Check if tool output is truncated.

#### 2. The "Hallucination" (ImportError/AttributeError)
*   **Symptom:** `ModuleNotFoundError`, `AttributeError`, or `TypeError` in the execution logs.
*   **Trace Sign:** The agent uses `write_file` *without* first using `search_files` or `get_module_help` to verify the API.
*   **Fix:** Strict instructions: "You must verify all imports using `search_files` before using them."

#### 3. The "Context Poisoning"
*   **Symptom:** The agent starts writing generic code or forgets the specific task instructions.
*   **Trace Sign:** The prompt token count is massive (>30k). The user prompt is buried under pages of `read_file` output.
*   **Fix:** Switch to **Abstracted Inspection** (Discovery Strategy). Stop reading full files; use `read_definitions` or `get_module_help`.

#### 4. The "Lazy Coder"
*   **Symptom:** The agent writes `... rest of code ...` or `pass` in the final solution.
*   **Trace Sign:** A `write_file` call contains incomplete code.
*   **Fix:** Update instructions to explicitly forbid placeholders in the final output.

#### 5. The "Attribute Guessing" Trap
*   **Symptom:** `AttributeError: 'X' object has no attribute 'y'` (e.g., `InvocationContext` has no attribute `request`).
*   **Trace Sign:** The agent accesses a property (like `.input` or `.request`) on a complex object without first inspecting it with `get_module_help`.
*   **Fix:** Mandate field verification. The agent must use `get_module_help(type_name)` to see the Pydantic fields before accessing them.

## Reference: The ADK Optimization Trajectory

| Iteration | Topology | Discovery | Memory | Result | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Single Agent | Context Injection | Full | **Fail** (50k tokens) | *Remove injection.* |
| **2** | Single Agent | Naive Grep | Full | **Fail** (45k tokens) | *Switch to Read File.* |
| **3** | Markovian Chain | Read File | Isolated | **Partial** (12k tokens) | *Switch Topology.* |
| **4** | **Single ReAct** | **Abstracted Tool** | **Windowed** | **Success** (15k, 54%) | *Switch Topology.* |
| **14**| **Deterministic Chain** | **Smart Fetcher** | **Isolated** | **Architecture Pass** (2.7k, 0%) | *Fix Import Quirk.* |