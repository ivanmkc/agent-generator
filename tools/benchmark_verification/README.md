# Benchmark Verification Tools

This directory contains tools for validating the integrity of benchmark definitions, specifically ensuring that API references (classes, methods) used in the YAML files actually exist in the target codebase.

## Tools

### `extract_apis_llm.py`
Scans all `benchmark.yaml` files in `benchmarks/benchmark_definitions` and extracts potential API references (Fully Qualified Names). It uses `tools/benchmark_generator/data/ranked_targets.yaml` to validate matches against known ADK entities.

**Usage:**
```bash
env/bin/python tools/benchmark_verification/extract_apis_llm.py
```
**Output:** `extracted_apis_llm.yaml` (in project root).

### `verify_apis.py`
Takes the output from the extraction step (`extracted_apis_llm.yaml`) and dynamically attempts to import each API from the `adk-python` source code. This confirms existence and accessibility.

**Usage:**
```bash
env/bin/python tools/benchmark_verification/verify_apis.py
```
**Output:** `api_verification_report.yaml` (in project root).


