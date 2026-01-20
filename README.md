# Agent Generator

This repository contains tools and benchmarks for generating and evaluating AI agents using the Agent Development Kit (ADK).

## Project Structure

- **benchmarks/**: Contains benchmark definitions, generators, and runner infrastructure.
  - `benchmark_definitions/`: YAML files defining specific benchmark cases (e.g., API understanding, error fixing).
  - `benchmark_generator/`: Tools for generating benchmarks from data sources.
  - `answer_generators/`: Implementations of agents/systems that attempt to solve the benchmarks.
  - `runner/`: Infrastructure for executing benchmarks and collecting results.

- **tools/**: Utility scripts for analysis, maintenance, and verification.
  - `extract_apis_llm.py`: Tool for extracting API references from benchmark definitions.
  - `verify_apis.py`: Tool for verifying that extracted APIs exist in the ADK codebase.

- **repos/**: Contains vendored or referenced repositories (e.g., `adk-python`).

## Usage

### Running Benchmarks
(Instructions for running benchmarks would go here, e.g., `python benchmarks/run.py ...`)

### Verifying Benchmarks
To verify that the API references in the benchmark YAML files are valid:

1. Extract API references:
   ```bash
   env/bin/python tools/extract_apis_llm.py
   ```

2. Verify existence:
   ```bash
   env/bin/python tools/verify_apis.py
   ```

This will produce `extracted_apis_llm.yaml` and `api_verification_report.yaml`.
