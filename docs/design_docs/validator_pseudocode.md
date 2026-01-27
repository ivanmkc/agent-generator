# Validator Pseudocode: Statistical Impact Scoring via Context Injection

## Overview
We quantify the relevance of specific contexts (FQNs) by measuring their **impact** on the success rate of solving a benchmark query. The validator dynamically builds a candidate pool and injects randomized subsets into the prompt to measure causal lift.

## 1. Candidate Selection (Pooling)

The validator is responsible for defining its own search space. It does not expect candidates to be pre-populated.

```python
async def _generate_candidate_pool(self, case: RetrievalCase) -> List[RetrievalContext]:
    """
    Constructs the universe of candidates for the Monte Carlo simulation from scratch.
    """
    candidates = {}
    
    # A. Mine "Gold" Candidates (Heuristic / Metadata)
    # We look at the Ground Truth to find high-probability candidates.
    if case.source == "api_understanding":
        # Extract from answer FQNs
        for fqn in case.ground_truth['answers_fqns']:
            candidates[fqn] = self.fetch_context(fqn, source="gold_heuristic")
elif case.source == "fix_errors":
        # Extract from imports in solution code
        for fqn in self.extract_imports(case.ground_truth['fixed_file']):
            candidates[fqn] = self.fetch_context(fqn, source="gold_heuristic")
        
    # B. Vector Search (Hard Negatives / Missed Positives)
    # We use a strong Retriever to find what a real search system would find.
    retrieved = await self.retriever.search(case.query, top_k=15)
    for t in retrieved:
        if t.id not in candidates:
            candidates[t.id] = RetrievalContext(
                fqn=t.id, text=t.docstring, source="vector_search"
            )
            
    # C. Random Negatives (Control Group)
    # Add 5 random docs to measure baseline noise tolerance.
    random_docs = self.corpus.sample_random(5)
    for t in random_docs:
        if t.id not in candidates:
            candidates[t.id] = RetrievalContext(
                fqn=t.id, text=t.docstring, source="random_noise"
            )
            
    return list(candidates.values())
```

## 2. Monte Carlo Validation Loop
 
### 2.1 Sampling Density (The "Kernel" Size)
We use **Bernoulli Sampling with p=0.5**.
*   **Logic:** Every candidate in the pool has an independent 50% probability of being included in a trial.
*   **Average Trial Size:** `0.5 * Pool_Size` (e.g., for a pool of 20, trials average 10 documents).
*   **Statistical Rationale:** `p=0.5` provides the maximum number of unique combinations (highest entropy), allowing us to most effectively isolate the "Delta P" (impact) of each document across multiple trials.

### 2.2 Context Injection Format
Documents are injected into the system prompt as a structured text block:

```text
DOCUMENTATION CONTEXT:
The following ADK symbols are available for reference. Use them to answer the query.

[START_DOCUMENT: google.adk.agents.llm_agent.LlmAgent]
Class LlmAgent:
LLM-based Agent implementation...
[END_DOCUMENT]

[START_DOCUMENT: google.adk.tools.function_tool.FunctionTool]
Class FunctionTool:
A tool that wraps a user-defined Python function...
[END_DOCUMENT]
```

### 2.3 The Logic

```python
class DataValidator:
    
    async def validate_case(self, case: RetrievalCase):
        # 1. Generate Candidate Pool (Internal Logic)
        candidates = await self._generate_candidate_pool(case)
        fqn_map = {c.fqn: c for c in candidates}
        
        # Statistics Containers
        stats = {fqn: {'success_in': 0, 'trials_in': 0, 'success_out': 0, 'trials_out': 0} for fqn in fqn_map}
        
        # 2. Monte Carlo Loop
        for _ in range(N_TRIALS):
            # a. Sample a subset (p=0.5 per item)
            subset_fqns = [f for f in fqn_map if random.random() > 0.5]
            
            # b. Construct Prompt with Structured Injection
            combined_context = "\n\n".join([
                f"[START_DOCUMENT: {f}]\n{fqn_map[f].text}\n[END_DOCUMENT]" 
                for f in subset_fqns
            ])
            
            # c. Attempt Task (Single Shot Pass@1)
            answer = await self.generate_answer(case.query, combined_context)
            
            # d. Validate Answer via Benchmark Runner
            is_correct = self.benchmark_runner.validate(case, answer)
            
            # e. Update Stats
            for f in fqn_map:
                if f in subset_fqns:
                    stats[f]['trials_in'] += 1
                    if is_correct: stats[f]['success_in'] += 1
                else:
                    stats[f]['trials_out'] += 1
                    if is_correct: stats[f]['success_out'] += 1

        # 3. Calculate Impact Scores (Delta P)
        for f in stats:
            p_in = stats[f]['success_in'] / stats[f]['trials_in'] if stats[f]['trials_in'] > 0 else 0
            p_out = stats[f]['success_out'] / stats[f]['trials_out'] if stats[f]['trials_out'] > 0 else 0
            
            impact_score = p_in - p_out
            fqn_map[f].metadata.update({'impact_score': impact_score, 'p_in': p_in, 'p_out': p_out})

        case.candidates = list(fqn_map.values())
        return case
```