# Agent Generator

This repository contains tools and benchmarks for generating and evaluating AI agents using the Agent Development Kit (ADK).

## Project Structure

```text
.
├── ai/                         # AI Inputs & Outputs
│   ├── instructions/           # Instructions, Prompts, Knowledge Base
│   │   ├── experiments/        # Historical experiment instructions
│   │   ├── knowledge/          # ADK Knowledge Index & Stats
│   │   ├── prompts/            # System Prompts for Analysis
│   │   └── datasets/           # Synthetic Datasets
│   └── reports/                # Generated Reports, Logs, & Doc Caches
│
├── benchmarks/                 # Execution Framework & Definitions
│   ├── answer_generators/      # Candidate agents (ADK, Gemini, etc.)
│   ├── benchmark_definitions/  # YAML test cases (API understanding, Fix Error)
│   ├── runner/                 # Execution environments (Pytest, Docker)
│   └── tests/                  # Integration tests for the framework
│
├── scripts/                    # Helper Scripts
│   └── benchmark_run.sh        # Main entry point for running benchmarks
│
├── tools/                      # Utilities & Generators
│   ├── analysis/               # Forensic Analysis Engine
│   ├── benchmark_generator/    # Agentic Benchmark Generator
│   ├── benchmark_verification/ # API Verification Tools
│   ├── debugging/              # Debugging Scripts
│   ├── knowledge/              # Knowledge Indexing Tools
│   ├── target_ranker/          # Static Analysis & Prioritization
│   └── viewer/                 # Visualization Tools
│
├── repos/
│   └── adk-python/             # The target codebase (Vendored)
│
└── ...
```

### Key Directories

- **ai/**: Centralized directory for all AI-related context.
    - **instructions/**: Input data (prompts, knowledge, experiment specs).
    - **reports/**: Output artifacts (analysis reports, generated documentation).
- **benchmarks/**: The core execution engine. It loads YAML definitions and runs `AnswerGenerator` implementations against them.
- **scripts/**: Convenience scripts for common tasks.
- **tools/benchmark_generator/**: An autonomous system that scans the `repos/` and generates new benchmark YAMLs.
- **tools/analysis/**: A hybrid (LLM + Stats) engine for analyzing why agents fail.

## Usage

### Running Benchmarks
Use the provided script to run benchmarks:
```bash
./scripts/benchmark_run.sh notebooks/run_benchmarks.py --suite-filter "debug"
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
