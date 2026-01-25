# Validator Pseudocode: Statistical Impact Scoring via Context Injection

## Overview
We quantify the relevance of specific contexts (FQNs) by measuring their **impact** on the success rate of solving a benchmark query. The validator dynamically builds a candidate pool from a raw `BenchmarkCase` and measures causal lift via Monte Carlo trials.

## 1. Data Models

We use the existing `BenchmarkCase` hierarchy (`ApiUnderstandingBenchmarkCase`, `FixErrorBenchmarkCase`, `MultipleChoiceBenchmarkCase`) directly. We do not use a separate `RetrievalCase` wrapper.

```python
class RetrievalContext(BaseModel):
    """
    A candidate document being evaluated for impact.
    """
    fqn: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict) # Stores impact_score, p_in, etc.
```

## 2. Candidate Selection (Pooling)

The validator is responsible for defining its own search space based on the case type.

```python
async def _generate_candidate_pool(
    self, 
    case: BenchmarkCase, 
    top_k_retrieved: int = 15, 
    n_random_negatives: int = 5
) -> List[RetrievalContext]:
    """
    Constructs the universe of candidates for the Monte Carlo simulation from scratch.
    """
    candidates = {}
    
    # A. Mine "Gold" Candidates (Heuristic / Metadata)
    if isinstance(case, ApiUnderstandingBenchmarkCase):
        # Extract from answer FQNs
        for answer in case.answers:
            for fqn in answer.fully_qualified_class_name:
                candidates[fqn] = self.fetch_context(fqn)
                
    elif isinstance(case, FixErrorBenchmarkCase):
        # Extract from imports in solution code
        if case.fixed_file:
            for fqn in self.extract_imports(case.fixed_file):
                candidates[fqn] = self.fetch_context(fqn)
                
    elif isinstance(case, MultipleChoiceBenchmarkCase):
        # Extract from explanation or correct option mapping if available
        # (This might require an LLM pass to extract FQNs from the text if not structured)
        pass 
        
    # B. Vector Search (Hard Negatives / Missed Positives)
    # Query: case.question (MC/API) or case.description (FixError)
    query_text = self._get_query_text(case)
    retrieved = await self.retriever.search(query_text, top_k=top_k_retrieved)
    for t in retrieved:
        if t.id not in candidates:
            candidates[t.id] = RetrievalContext(fqn=t.id, text=t.docstring)
            
    # C. Random Negatives (Noise/Control Group)
    random_docs = self.corpus.sample_random(n_random_negatives)
    for t in random_docs:
        if t.id not in candidates:
            candidates[t.id] = RetrievalContext(fqn=t.id, text=t.docstring)
            
    return list(candidates.values())
```

## 3. Monte Carlo Validation Loop

### 3.1 Logic

```python
class DataValidator:
    
    async def validate_case(self, case: BenchmarkCase) -> List[RetrievalContext]:
        # 1. Generate Candidate Pool
        pool = await self._generate_candidate_pool(case, top_k_retrieved=15, n_random_negatives=5)
        fqn_map = {c.fqn: c for c in pool}
        
        # Statistics Containers
        stats = {fqn: {'success_in': 0, 'trials_in': 0, 'success_out': 0, 'trials_out': 0} for fqn in fqn_map}
        
        # 2. Monte Carlo Loop
        for _ in range(N_TRIALS):
            # a. Sample a subset (p=0.5)
            subset_fqns = [f for f in fqn_map if random.random() > 0.5]
            
            # b. Construct Prompt with Injected Context
            combined_context = "\n\n".join([
                f"[START_DOCUMENT: {f}]\n{fqn_map[f].text}\n[END_DOCUMENT]" 
                for f in subset_fqns
            ])
            
            # c. Attempt Task (Single Shot)
            # Uses the case-specific prompt generation logic
            answer = await self.generate_answer(case, combined_context)
            
            # d. Validate Answer via Runner (Pass/Fail)
            # Uses case.runner.validate_answer(...)
            runner = case.runner
            is_correct = runner.validate(case, answer)
            
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
            fqn_map[f].metadata.update({'impact_score': impact_score})

        # Return the verified contexts directly
        return list(fqn_map.values())
```
