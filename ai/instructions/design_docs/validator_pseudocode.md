# Validator Pseudocode: Statistical Impact Scoring via Context Injection

## Overview
We quantify the relevance of specific contexts (FQNs) by measuring their **impact** on the success rate of solving a benchmark query. The validator supports two sampling strategies: **Fixed Trials** (Constant) and **Adaptive Trials** (Statistical Convergence).

## 1. Candidate Selection (Pooling)

The validator dynamically builds a candidate pool from a raw `BenchmarkCase`.

```python
async def _generate_candidate_pool(
    self, 
    case: BenchmarkCase, 
    top_k_retrieved: int = 15, 
    n_random_negatives: int = 5
) -> List[RetrievalContext]:
    # ... (Logic to pool Gold, Vector Search, and Random candidates)
    return candidates
```

## 2. Monte Carlo Validation Loop

```python
class DataValidator:
    
    async def validate_case(
        self, 
        case: BenchmarkCase, 
        mode: Literal["fixed", "adaptive"] = "fixed",
        max_n: int = 20,
        min_n: int = 5,
        se_threshold: float = 0.05
    ) -> List[RetrievalContext]:
        """
        Quantifies the impact of each context via Monte Carlo trials.
        
        Args:
            mode: "fixed" uses max_n trials. "adaptive" stops early if statistics converge.
            max_n: Maximum trials to run.
            min_n: Minimum trials before checking convergence.
            se_threshold: Target Standard Error for early stopping.
        """
        pool = await self._generate_candidate_pool(case)
        stats = {fqn: {'success_in': 0, 'trials_in': 0, 'success_out': 0, 'trials_out': 0} for fqn in pool}
        
        for n in range(max_n):
            # a. Sample subset (p=0.5)
            subset = [c for c in pool if random.random() > 0.5]
            
            # b. Run Trial (Inject Context -> Generate -> Validate)
            is_correct = await self.run_trial(case, subset)
            
            # c. Update Stats
            self.update_stats(stats, subset, is_correct)
            
            # d. Optional: Early Stopping (Adaptive Mode)
            if mode == "adaptive" and n >= min_n:
                if self.is_converged(stats, se_threshold):
                    print(f"Reached convergence at trial {n}. Stopping.")
                    break

        return self.calculate_impact_scores(stats)

    def is_converged(self, stats, threshold):
        """
        Checks if the Standard Error of Delta P for the top candidate 
        is below the target threshold.
        """
        for fqn in stats:
            p = stats[fqn]['success_in'] / stats[fqn]['trials_in'] if stats[fqn]['trials_in'] > 0 else 0
            se = math.sqrt(p * (1-p) / stats[fqn]['trials_in'])
            if se > threshold:
                return False # Still too much variance
        return True
```

## 3. Metrics: Impact Score (Delta P)
For each document, we output a scalar score:
$$\text{Impact} = P(\text{Success} | \text{Present}) - P(\text{Success} | \text{Absent})$$

*   **YES (+):** Document significantly improves success rate.
*   **NO (0):** Document has no measurable impact.
*   **TOXIC (-):** Document actively confuses the model.

```