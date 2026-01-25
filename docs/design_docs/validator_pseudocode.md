# Validator Pseudocode: Agentic Monte Carlo with Statistical Impact Scoring

## Overview
We quantify the relevance of specific contexts (FQNs) by measuring their **impact** on the success rate of solving a benchmark query. We do not make a binary YES/NO decision; instead, we output a scalar score representing the conditional dependence.

## Architecture

```python
class DataValidator:
    
    async def validate_case(self, case: RetrievalCase):
        """
        Quantifies the impact of each context via Monte Carlo trials.
        """
        
        # 1. Candidate Pool
        # Mix of Gold (from metadata), Hard Negatives (Vector Search), and Random Negatives
        candidates = case.positive_ctxs + case.negative_ctxs
        fqn_map = {c.fqn: c for c in candidates}
        
        # Statistics Containers
        # trials_in[fqn]: # of trials where FQN was PRESENT
        # success_in[fqn]: # of SUCCESSFUL trials where FQN was PRESENT
        stats = {
            fqn: {
                'success_in': 0, 'trials_in': 0, 
                'success_out': 0, 'trials_out': 0
            } 
            for fqn in fqn_map
        }
        
        # 2. Monte Carlo Loop
        for _ in range(N_TRIALS):
            # a. Sample a subset (Bernoulli p=0.5)
            # This forms the "Available Knowledge Kernel" for this trial.
            subset_fqns = sample(candidates, p=0.5)
            subset_ctxs = [fqn_map[f] for f in subset_fqns]
            
            # b. Construct Prompt with Injected Context
            # No tool use; strictly inject the subset into the context window.
            combined_context = "\n".join([c.text for c in subset_ctxs])
            
            # c. Attempt Task (Single Shot)
            # The model attempts to solve the task using ONLY the injected context.
            answer = await self.generate_answer(case.query, combined_context)
            
            # d. Validate Answer
            # Use the official benchmark runner to determine correctness (Pass/Fail).
            is_correct = self.benchmark_runner.validate(case, answer)
            
            # e. Update Stats (Causal Attribution)
            for fqn in fqn_map:
                if fqn in subset_fqns:
                    stats[fqn]['trials_in'] += 1
                    if is_correct: stats[fqn]['success_in'] += 1
                else:
                    stats[fqn]['trials_out'] += 1
                    if is_correct: stats[fqn]['success_out'] += 1

        # 3. Calculate Impact Scores (Delta P)
        # Impact = P(Success | Context Present) - P(Success | Context Absent)
        for fqn in stats:
            p_in = stats[fqn]['success_in'] / stats[fqn]['trials_in']
            p_out = stats[fqn]['success_out'] / stats[fqn]['trials_out']
            
            impact_score = p_in - p_out
            
            # Update the dataset with the scalar score
            fqn_map[fqn].metadata['impact_score'] = impact_score
            fqn_map[fqn].metadata['p_in'] = p_in
            fqn_map[fqn].metadata['p_out'] = p_out

        # The final dataset contains the raw scalar scores for downstream analysis/ranking.
        # No hard thresholding is applied here.
        return case
```