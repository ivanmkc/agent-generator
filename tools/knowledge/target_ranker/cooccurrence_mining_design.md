# Co-occurrence & Target Ranker Architecture

This document describes the architectural flow of mining usage probabilities for Python components across target and sample repositories.

## Overview

When the Agentic Generator constructs benchmarking scenarios or when developers browse the codebase context index, it relies heavily on the `RANKED_TARGETS` hierarchy. This hierarchy scores and organizes the underlying codebase elements (e.g. `Client()`, `GenerateContentConfig()`) primarily based on their real-world usage patterns.

This data is sourced by `tools/knowledge/run_cooccurrence_indexing.py` which computes conditional probabilities of two entities appearing within the same file (e.g., `P(target | context)`).  

## 1. Registry Configuration & Orchestration (`manage_registry.py`)

The knowledge generation is centrally driven by `registry.yaml` handled by `manage_registry.py`.

```yaml
repositories:
  google/adk-python:
    repo_url: https://github.com/google/adk-python.git
    sample_repos:
      - https://github.com/google/adk-samples.git
    namespaces:
      - google.genai
```

### Flow:
1. `manage_registry.py` processes a version-update request (e.g. `v1.24.1`).
2. It clones the main `repo_url` checked out exactly to `v1.24.1` into a temporary build space.
3. It shallow-clones the default branches of all associated `sample_repos`.
4. It passes this combined list of target paths explicitly to `generate_cooccurrence()`.

## 2. Dynamic Namespace Discovery & Indexing (`run_cooccurrence_indexing.py`)

The tracking indexer crawls over every Python (`.py`) file in the provided list of checkout targets.
It employs a specialized `ast.NodeVisitor` (`GranularUsageVisitor`) to track module imports, class instantiations, and attribute paths.

### Tracking Scheme:
* If explicit `namespaces` are provided via YAML (or CLI), the parser ONLY tracks those module roots.
* **Dynamic Mode**: If no namespaces are provided (`namespaces: []`), the visitor captures *everything*, subsequently pulling the root module and filtering it rigidly against `sys.stdlib_module_names`. This efficiently eliminates tracking useless associations like `os`, `sys`, or `json`, allowing the tracker to organically discover external dependency pairings (e.g., `pydantic.BaseModel` usage alongside `langchain`).

The final aggregated map filters out noise (entities with `< 2` supports across the fleet) and outputs `cooccurrence.yaml` containing strongly-typed `CooccurrenceAssociation` entries (governed by Pydantic schemas).

## 3. Resolving Hallucinations against Target Ranker (`ranker.py`)

A major architectural challenge is **version skewing**: external repositories (`sample_repos`) are rarely explicitly pinned to the exact release being checked out by the registry automation. 
Consequently, `cooccurrence.yaml` will often contain referenced classes or methods that have been deprecated or newly implemented mismatching the target libraries literal codebase. 

`TargetRanker` explicitly resolves these hallucinations during the generation step (`tools/knowledge/target_ranker/run_ranker.py`):
1. **Rigid Extraction**: The `TargetRanker` runs a static AST scan across *only* the pinned core target checkout (ignoring samples completely). It constructs an exact structural map of the literal codebase.
2. **Heuristic Weighting**: It then `yaml.safe_load`s the generated `cooccurrence.yaml` file to use strictly as a weighting heuristic.
3. **Implicit Filtration**: It checks the probability matrix components against its strict AST map. If a recorded component in the external co-occurrence data does not exist in the rigid target layout, it drops it. 

This enables `manage_registry` to perpetually mine thousands of external legacy scripts entirely decoupled from core target repository versions without polluting the generated `ranked_targets.yaml` dataset.
