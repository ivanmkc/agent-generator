# Agent Generator

This repository contains tools and benchmarks for generating and evaluating AI agents using the Agent Development Kit (ADK).

## Project Structure

```text
.
├── benchmarks/                 # Execution Framework & Definitions
│   ├── answer_generators/      # Candidate agents (ADK, Gemini, etc.)
│   ├── benchmark_definitions/  # YAML test cases (API understanding, Fix Error)
│   ├── runner/                 # Execution environments (Pytest, Docker)
│   ├── tests/                  # Integration tests for the framework
│   ├── benchmark_orchestrator.py
│   └── benchmark_runner.py
│
├── tools/                      # Utilities & Generators
│   ├── benchmark_generator/    # Agentic Benchmark Generator (Agentic)
│   │   ├── agents.py           # Multi-agent orchestration
│   │   ├── tools.py            # Sandbox & Truth Lab tools
│   │   └── run_generator.py    # Entry point
│   │
│   ├── target_ranker/          # Static Analysis & Prioritization
│   │   ├── ranker.py           # Ranking logic (BFS, Usage)
│   │   ├── scanner.py          # AST Scanner & Type Resolver
│   │   └── models.py           # Data schemas (RankedTarget)
│   │
│   ├── analysis/               # Forensic Analysis Engine
│   ├── cli/                    # CLI tools (audit_failures, generate_report)
│   ├── retrieval_dataset_generation/
│   └── benchmark_verification/ # API Verification Tools
│
├── repos/
│   └── adk-python/             # The target codebase (Vendored)
│
└── ...
```

### Key Directories

- **benchmarks/**: The core execution engine. It loads YAML definitions and runs `AnswerGenerator` implementations against them.
- **tools/benchmark_generator/**: An autonomous system that scans the `repos/` and generates new benchmark YAMLs.
- **tools/target_ranker/**: A deterministic tool that maps the codebase structure and ranks APIs by importance/usage.
- **tools/analysis/**: A hybrid (LLM + Stats) engine for analyzing why agents fail.

## Usage

### Running Benchmarks
(Instructions for running benchmarks would go here, e.g., `python benchmarks/run.py ...`)

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