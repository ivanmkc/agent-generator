# Design Doc: Advanced Statistical API Discovery

**Status:** Proposed
**Author:** Gemini CLI Agent
**Date:** 2026-01-10

## 1. Executive Summary
The current API discovery mechanism for agents (`get_module_help`) provides an exhaustive but noisy dump of all members in a Python module. This leads to high token consumption and increased hallucination rates as agents struggle to identify the most relevant parameters. This document proposes an advanced discovery tool that uses **Static Analysis (AST)** and **Usage Statistics** to surface only the most critical "Happy Path" components of an API.

## 2. Problem Statement
*   **Token Bloat:** Complex modules (e.g., `google.adk.agents`) can exceed 5k tokens in a single `inspect` call.
*   **Parameter Paralysis:** LLMs often guess parameter names (e.g., `model_name` vs `model`) because they see 20+ optional arguments and lose track of the core signature.
*   **Context Fragmentation:** Agents spend multiple turns navigating the filesystem to find definitions that should be easily discoverable via module FQNs.

## 3. Proposed Solution: Statistical API Filtering
We will move from **Reflection-based discovery** (runtime `inspect`) to **Statistical discovery** based on a pre-calculated index of the repository's own code, tests, and examples.

### 3.1. Key Innovation: Arcs & Frequencies
Instead of showing every argument, the tool will return arguments weighted by their **Usage Frequency** in the rest of the codebase.
*   **Definition Arc:** The relationship between a function call and its definition.
*   **Statistical Weighting:** If `LlmAgent` is called 100 times in `tests/` and `examples/`, and the `model` argument is passed 99 times while `chat_history` is passed 2 times, `model` is prioritized.

### 3.2. Injectable Filtering Strategies
The filtering logic is decoupled from the core tool. The tool accepts a `FilteringStrategy` instance, allowing complete control over the pruning logic without polluting the tool's signature.

1.  **`TokenBudgetStrategy(max_tokens=1000)`**: Prioritizes members and arguments to fit within a token budget.
2.  **`ThresholdStrategy(min_frequency=0.2)`**: Filters by usage percentage.
3.  **`ExhaustiveStrategy()`**: No filtering (fallback).

## 4. Architecture

### 4.1. The Indexer (`tools/api_indexer.py`)
A background process that runs on the repository to generate `api_metadata.yaml`.
1.  **AST Parsing:** Uses `ast.NodeVisitor` to find all `FunctionDef` and `ClassDef` nodes.
2.  **Call Site Analysis:** Finds all `Call` nodes. Resolves the called function to its definition.
3.  **Metric Collection:** `call_count`, `arg_usage`, `co_occurrence`.

### 4.2. The Discovery Tool (`get_module_help_v2`)
1.  **Input:** `module_name`, `target_symbol` (optional), `strategy: FilteringStrategy`.
2.  **Logic:**
    *   Load pre-computed stats from YAML.
    *   Delegate filtering to the provided `strategy` instance.
    *   Render the filtered view as a Python stub string.

## 5. Data Model (`api_metadata.yaml`)
```yaml
google.adk.agents.llm_agent.LlmAgent:
  usage_rank: 1
  total_calls: 245
  init_args:
    name:
      required: true
      freq: 1.0
    model:
      required: false
      freq: 0.98
    instruction:
      required: false
      freq: 0.92
```

## 6. User Experience (Agent Perspective)
The agent uses the tool via a standard interface, with the strategy pre-configured by the runner.
```python
# Agent calls the tool
get_module_help('google.adk.agents', target_symbol='LlmAgent')

# Output is pruned and annotated
class LlmAgent(BaseAgent):
    def __init__(
        self, 
        name: str,          # REQUIRED
        model: str,         # Used in 98% of cases
        instruction: str,   # Used in 92% of cases
        # ... + 15 rare arguments hidden
    ):
```

## 9. API Specification

### 9.1 Indexer API (`tools.api_indexer`)

```python
from pydantic import BaseModel
from typing import List, Optional

class RepoConfig(BaseModel):
    url: str
    branch: str = "main"
    include_paths: Optional[List[str]] = None
    exclude_paths: Optional[List[str]] = None
    
class IndexerConfig(BaseModel):
    sources: List[RepoConfig]
    output_path: str = "api_metadata.yaml"
    min_usage_threshold: int = 2 

def build_index(config: IndexerConfig) -> None:
    """Clones repos and builds the statistical AST index in YAML format."""
    pass
```

### 9.2 Discovery Tool API (`AdkTools`)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# --- Strategy Interface ---

class FilteringStrategy(ABC):
    """Abstract base class for API filtering strategies."""

    @abstractmethod
    def filter_members(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def filter_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pass

# --- Concrete Strategy Implementation ---

class TokenBudgetStrategy(FilteringStrategy):
    def __init__(self, max_tokens: int = 1000):
        self.max_tokens = max_tokens

    def filter_members(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Greedy implementation based on self.max_tokens
        pass

    def filter_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Greedy implementation based on frequency
        pass

# --- The Tool ---

class StatisticalDiscoveryTool:
    def __init__(self, index_path: str):
        self.index = self._load_index_from_yaml(index_path)

    def get_module_help(
        self, 
        module_name: str, 
        target_symbol: Optional[str] = None, 
        strategy: Optional[FilteringStrategy] = None
    ) -> str:
        """
        Returns a curated summary of a module's API.
        
        Args:
            module_name: FQN of the module.
            target_symbol: Specific class/function to focus on.
            strategy: An instance of FilteringStrategy. 
                      Defaults to TokenBudgetStrategy(1000) if None.
        """
        # 1. Default fallback
        strategy = strategy or TokenBudgetStrategy(max_tokens=1000)

        # 2. Get data from index
        raw_data = self.index.get(module_name, {})

        # 3. Apply Strategy Instance
        filtered_members = strategy.filter_members(raw_data.get('members', []))
        # ... logic to apply strategy to arguments ...

        # 4. Render output
        return self._render_python_stub(filtered_members)
```

### 9.3 Usage Example (CLI)

```bash
# Configuration file: sources.yaml
# sources:
#   - url: https://github.com/google/adk-python
#     include_paths: ["examples", "tests"]

# Run the indexer
python tools/api_indexer.py --config sources.yaml --output benchmarks/adk_stats.yaml
```
