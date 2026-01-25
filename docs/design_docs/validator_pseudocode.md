# Validator Pseudocode: Agentic Monte Carlo with Tool Gating

## Overview
We evaluate the relevance of specific contexts (FQNs) by running multiple trials where an agent attempts to solve the benchmark query. In each trial, the agent is restricted to a randomized subset of the candidate contexts.

## Architecture

```python
class DataValidator:
    
    async def validate_pair(self, pair: RetrievalPair):
        """
        Determines empirical relevance of each context via Monte Carlo trials.
        """
        
        # 1. Candidate Pool
        # Mix of Gold (from metadata) and Negatives (random samples)
        candidates = pair.positive_ctxs + pair.negative_ctxs
        fqn_map = {c.fqn: c for c in candidates}
        
        # Statistics
        stats = {fqn: {'success_with': 0, 'trials_with': 0, ...} for fqn in fqn_map}
        
        # 2. Monte Carlo Loop
        for _ in range(N_TRIALS):
            # a. Sample a subset (Bernoulli p=0.5)
            # This forms the "Available Knowledge Kernel" for this trial.
            subset_fqns = sample(candidates)
            
            # b. Construct the Gatekeeper Tool
            # This tool wraps the logic to retrieve docstrings but enforces the subset boundary.
            tools = [self._create_gated_tool(subset_fqns, fqn_map)]
            
            # c. Construct Prompt
            # Explicitly lists *only* the available symbols to guide the agent.
            prompt = f"""
            Task: {pair.query}
            
            Available Symbols in this Environment:
            {list(subset_fqns)}
            
            Instructions:
            1. You MUST use `inspect_adk_symbol(fqn)` to read documentation.
            2. You are RESTRICTED to the symbols listed above.
            3. Answer the question based ONLY on the inspected information.
            """
            
            # d. Agent Execution (Multi-Turn)
            # The agent explores the allowed subset using the tool.
            answer = await self.agent.run(prompt, tools)
            
            # e. Validation
            is_correct = self.benchmark_runner.validate(pair, answer)
            
            # f. Update Stats
            for fqn in fqn_map:
                if fqn in subset_fqns:
                    stats[fqn]['trials_with'] += 1
                    if is_correct: stats[fqn]['success_with'] += 1
                else:
                    stats[fqn]['trials_without'] += 1
                    if is_correct: stats[fqn]['success_without'] += 1

        # 3. Calculate Delta P
        # Relevance = P(Success | In) - P(Success | Out)
        for fqn in stats:
            p_in = stats[fqn]['success_with'] / stats[fqn]['trials_with']
            p_out = stats[fqn]['success_without'] / stats[fqn]['trials_without']
            
            if (p_in - p_out) > THRESHOLD:
                mark_relevant(fqn)
            else:
                mark_irrelevant(fqn)

    def _create_gated_tool(self, allowed_fqns, fqn_map):
        """
        Creates a callable tool that enforces the 'Closed World' assumption.
        """
        def inspect_adk_symbol(fqn: str):
            if fqn not in allowed_fqns:
                return f"Error: Symbol '{fqn}' is not available in this restricted environment."
            
            # Return the pre-fetched content (fast) 
            # OR call the actual codebase reader if preferred (slower but 'real')
            return fqn_map[fqn].text
            
        return inspect_adk_symbol
```
