# Validator Pseudocode: Statistical Impact Scoring via Context Injection

## Overview
We quantify the relevance of specific contexts (FQNs) by measuring their **impact** on the success rate of solving a benchmark query. The validator dynamically builds a candidate pool from a raw query and measures causal lift via Monte Carlo trials.

## 1. Data Models

The input to the validator is a raw `RetrievalCase`. It contains only the task definition and the data required to verify a solution. It contains **no context or candidate information**.

```python
class RetrievalCase(BaseModel):
    """
    A pure task definition mined from the benchmark suite.
    """
    id: str = Field(..., description="Unique benchmark ID (e.g. suite:slug)")
    query: str = Field(..., description="The natural language task/question")
    source: Literal["api_understanding", "fix_errors"]
    ground_truth: Dict[str, Any] = Field(
        ..., 
        description="Metadata for validation (e.g., answer string, path to test_file)"
    )

class RetrievalContext(BaseModel):
    """
    A candidate document being evaluated for impact.
    """
    fqn: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict) # Stores impact_score, p_in, etc.
```

## 2. Candidate Selection (Pooling)

The validator is responsible for defining its own search space.

```python
async def _generate_candidate_pool(
    self, 
    case: RetrievalCase, 
    top_k_retrieved: int = 15, 
    n_random_negatives: int = 5
) -> List[RetrievalContext]:
    """
    Constructs the universe of candidates for the Monte Carlo simulation from scratch.
    
    Args:
        top_k_retrieved: Number of candidates to fetch via Vector Search.
        n_random_negatives: Number of random noise documents to include.
    """
    candidates = {}
    
    # A. Mine "Gold" Candidates (Heuristic / Metadata)
    # Extract from Ground Truth to find high-probability candidates.
    if case.source == "api_understanding":
        for fqn in case.ground_truth['answers_fqns']:
            candidates[fqn] = self.fetch_context(fqn)
    elif case.source == "fix_errors":
        for fqn in self.extract_imports(case.ground_truth['fixed_file']):
            candidates[fqn] = self.fetch_context(fqn)
        
    # B. Vector Search (Hard Negatives / Missed Positives)
    # We use a strong Retriever to find what a real search system would find.
    retrieved = await self.retriever.search(case.query, top_k=top_k_retrieved)
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

### 3.1 Sampling Density
We use **Bernoulli Sampling with p=0.5**. Each candidate in the pool has an independent 50% probability of being included in a trial.

### 3.2 The Logic

```python
class DataValidator:
    
    async def validate_case(self, case: RetrievalCase) -> List[RetrievalContext]:
        # 1. Generate Candidate Pool
        pool = await self._generate_candidate_pool(case, top_k_retrieved=15, n_random_negatives=5)
        fqn_map = {c.fqn: c for c in pool}
        
        # Statistics Containers
        stats = {fqn: {'success_in': 0, 'trials_in': 0, 'success_out': 0, 'trials_out': 0} for fqn in fqn_map}
        
        # 2. Monte Carlo Loop
        for _ in range(N_TRIALS):
            # a. Sample a subset
            subset_fqns = [f for f in fqn_map if random.random() > 0.5]
            
            # b. Construct Prompt with Injected Context
            combined_context = "\n\n".join([
                f"[START_DOCUMENT: {f}]\n{fqn_map[f].text}\n[END_DOCUMENT]" 
                for f in subset_fqns
            ])
            
            # c. Attempt Task (Single Shot)
            answer = await self.generate_answer(case.query, combined_context)
            
            # d. Validate Answer via Runner (Pass/Fail)
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

        # Return the verified and scored candidates for this query
        return list(fqn_map.values())
```