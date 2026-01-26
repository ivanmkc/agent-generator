# Retrieval Dataset Generation Tools

This directory contains tools for creating, validating, and analyzing synthetic retrieval datasets derived from benchmarks.

## Overview

1.  **`extract_data.py`**: Mines existing benchmarks (API Understanding, Fix Errors, Multiple Choice) to create a raw `retrieval_dataset.yaml`.
2.  **`validate_data.py`**: Runs a Monte Carlo causal inference pipeline to empirically verify which documents are useful for solving each case.
3.  **`generate_report.py`**: Analyzes the validation logs and produces a human-readable Markdown report (`retrieval_analysis_report.md`).

## Usage

### 1. Extract Raw Data
```bash
python tools/retrieval_dataset_generation/extract_data.py
```
This generates `retrieval_dataset.yaml`.

### 2. Validate Data
```bash
python tools/retrieval_dataset_generation/validate_data.py --input retrieval_dataset.yaml --mode adaptive
```

**Options:**
- `--max-cases N`: Limit the run to the first N cases (useful for testing).
- `--mode [fixed|adaptive]`: 
    - `fixed`: Runs a fixed number of trials per case.
    - `adaptive`: Stops early if statistical convergence is reached (Recommended).
- `--resume`: Automatically resume from an existing output file if found (e.g. from a crashed run).
- `--overwrite`: Force a fresh start, overwriting any existing output.

**Interactive Resume:**
If you do not specify `--resume` or `--overwrite` and an existing run is detected, the tool will ask you whether to resume or start over.

### 3. Generate Report
```bash
python tools/retrieval_dataset_generation/generate_report.py --input retrieval_dataset_verified.yaml
```

## Methodology

See `docs/design_docs/synthetic_retrieval_dataset.md` for a deep dive into the statistical methods used (Monte Carlo, Delta P, Adaptive Convergence).