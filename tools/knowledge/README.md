# Knowledge Indexing Tools

Tools for building the static analysis index, probability graphs, and co-occurrence matrices used by the ADK Agents.

## Contents

- `generate_adk_index.py`: Scans the `repos/adk-python` and builds `ai/instructions/knowledge/adk_index.yaml`.
- `api_indexer.py`: Calculates usage statistics.
- `cooccurrence_indexer.py`: Builds the co-occurrence probability graph.
- `adk_chain_prob.py`: Utilities for chain probability calculations.
- `graph_adk_structure.py`: Visualizes the structure.

## Usage

To rebuild the index:
```bash
python tools/knowledge/generate_adk_index.py
```
