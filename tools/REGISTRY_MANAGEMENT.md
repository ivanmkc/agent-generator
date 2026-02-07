# Registry Management & Serial Update Workflow

This document outlines how to use the `manage_registry.py` tool to maintain the Codebase Knowledge Registry. The tool now supports a **serial update workflow** that automates cloning, ranking, embedding, and registry updating in a single command.

## Prerequisites

Ensure your environment has the necessary dependencies installed:
- `rich`
- `click`
- `pydantic`
- `pyyaml`
- `questionary` (for interactive checkboxes)
- `numpy` (for embeddings)
- `google-generativeai` (for embedding generation)

You can run the tool using:
```bash
python3 tools/manage_registry.py <command>
```
*(Or use the VS Code tasks if configured)*

## Workflow: Serial Update

The serial update process ensures that every version added to the registry is fully processed (Ranked + Embedded).

### Step 1: Check for Updates

Use the `check-updates` command to scan registered repositories for new git tags.

```bash
python3 tools/manage_registry.py check-updates
```

**Example Output:**
```text
Registry Updates
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Repository          ┃ Current Versions ┃ New Available    ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ google/adk-python   │ v0.2.2           │ v0.2.3, v0.2.4   │
│ google/generative-ai│ v0.3.0           │ Up to date       │
└─────────────────────┴──────────────────┴──────────────────┘
```

### Step 2: Apply Updates

Use the `update` command to interactively select and apply updates.

```bash
python3 tools/manage_registry.py update
```

**Interactive Selection:**

If `questionary` is installed, you will see a checkbox interface:
```text
? Select updates to apply:
  [ ] google/adk-python v0.2.3
  [ ] google/adk-python v0.2.4
```
*(Use arrow keys to move, Space to select, Enter to confirm)*

If `questionary` is missing, it falls back to text input:
```text
Available Updates
1. google/adk-python v0.2.3
2. google/adk-python v0.2.4

Tip: Install 'questionary' for checkbox selection: pip install questionary
Select updates to apply (comma-separated indices, 'all', or 'none') [none]: 2
```

**Execution Flow (Automated):**

Once you select a version (e.g., `v0.2.4`), the tool performs the following steps serially:

1.  **Cloning**: Clones the repository at the specific tag `v0.2.4` to a temporary directory.
    ```text
    Cloning https://github.com/google/adk-python (v0.2.4)...
    ```

2.  **Ranking**: Runs `run_ranker.py` to analyze the code and generate `ranked_targets.yaml`.
    ```text
    Generating Knowledge Index...
    Writing detailed YAML to .../indices/google-adk-python/v0.2.4/ranked_targets.yaml...
    Validation passed.
    Index generated at ...
    ```

3.  **Embedding**: **[NEW]** Runs `build_vector_index.py` to generate semantic vectors (`vectors.npy`) and keys (`vector_keys.yaml`).
    ```text
    Generating Semantic Embeddings...
    Successfully built index artifacts at .../indices/google-adk-python/v0.2.4
    Embeddings generated successfully.
    ```

4.  **Registering**: Updates `registry.yaml` with the new version info.
    ```text
    Registry updated. Added google/adk-python@v0.2.4.
    ```

### Step 3: Verify

The `registry.yaml` will now contain the new version, pointing to the generated index.

```yaml
repositories:
  google/adk-python:
    versions:
      v0.2.4:
        index_url: indices/google-adk-python/v0.2.4/ranked_targets.yaml
```

The `indices/google-adk-python/v0.2.4/` directory will contain:
- `ranked_targets.yaml` (The knowledge graph)
- `vectors.npy` (Semantic embeddings)
- `vector_keys.yaml` (Mapping of vectors to target IDs)

## VS Code Integration

You can also trigger these actions via VS Code Tasks:

-   **Regenerate Codebase Knowledge (Targets & Embeddings)**: This task runs the ranker and embedder for the *current* local repository state. It is useful for developing the ranker itself.
    -   Command: `PYTHONPATH=. env/bin/python tools/knowledge/target_ranker/run_ranker.py && PYTHONPATH=. env/bin/python tools/knowledge/build_vector_index.py`

## Troubleshooting

-   **"Embedding generation failed"**: Ensure `google-generativeai` is installed and you have a valid API key if required by the embedding script.
-   **"Registry not found"**: Ensure you are running from the project root or that the relative paths in `manage_registry.py` resolve correctly.
