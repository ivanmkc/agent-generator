# Agent Generator

This repository contains tools and benchmarks for generating and evaluating AI agents using the Agent Development Kit (ADK).

## Project Structure

```text
.
├── ai/                         # Design docs, prompts, and reports
├── benchmarks/                 # Benchmark definitions, answer generators, and runner logic
├── tools/                      # Core libraries and CLI tools
│   ├── cli/                    # User-facing scripts (run_benchmarks.sh, etc.)
│   ├── analysis/               # Analysis logic and notebooks
│   └── benchmark_generator/    # Tools for generating new benchmarks
├── env/                        # Virtual environment
└── ...
```

### Key Directories

- **ai/**: Centralized directory for all AI-related context.
    - **instructions/**: Input data (prompts, knowledge, experiment specs).
    - **reports/**: Output artifacts (analysis reports, generated documentation).
- **benchmarks/**: The core execution engine. It loads YAML definitions and runs `AnswerGenerator` implementations against them.
- **scripts/**: Convenience scripts for common tasks.
- **benchmarks.generator.benchmark_generator/**: An autonomous system that scans the `repos/` and generates new benchmark YAMLs.
- **tools/analysis/**: A hybrid (LLM + Stats) engine for analyzing why agents fail.

## Usage

### Running Benchmarks
Use the provided script to run benchmarks:
```bash
./tools/cli/run_benchmarks.sh --suite-filter "debug"
```

### Verifying Benchmarks
To verify that the API references in the benchmark YAML files are valid:

1. Extract API references:
   ```bash
   env/bin/python tools/benchmark_verification/extract_apis_llm.py
   ```

2. Verify existence:
   ```bash
   env/bin/python tools/benchmark_verification/verify_apis.py
   ```

This will produce `extracted_apis_llm.yaml` and `api_verification_report.yaml`.
