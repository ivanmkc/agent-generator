# Agent Generator

This repository contains tools and benchmarks for generating and evaluating AI agents using the Agent Development Kit (ADK).

## Project Structure

```text
.
├── core/                       # Standardized configuration, shared models, and utilities
├── ai/                         # Design docs, prompts, and reports
├── benchmarks/                 # Benchmark definitions and stable answer generators
│   └── generator/              # Tools for generating new benchmarks
├── experiments/                # Sandbox for experimental agent architectures (V46/V47)
├── tools/                      # Core libraries and CLI tools
│   └── cli/                    # User-facing scripts (run_benchmarks.sh, etc.)
├── data/                       # Unified directory for persistent runtime state
└── repos/                      # Vendored target repositories (adk-python)
```

### Key Directories

- **core/**: Centralized logic for the entire repo. Includes `config.py` (Pydantic Settings), `models.py` (shared schemas), and `api_key_manager.py`.
- **ai/**: Centralized directory for all AI-related context.
    - **instructions/**: Input data (prompts, knowledge, experiment specs).
    - **reports/**: Output artifacts (analysis reports, generated documentation).
- **benchmarks/**: The core execution engine. It loads YAML definitions and runs `AnswerGenerator` implementations against them.
- **experiments/**: Where new agent versions are developed and benchmarked before being moved to stable `answer_generators`.
- **benchmarks/generator/**: An autonomous system that scans the `repos/` and generates new benchmark YAMLs.
- **tools/analysis/**: A hybrid (LLM + Stats) engine for analyzing why agents fail.
- **data/**: The root for all persistent files created during runs (SQLite DBs, persistent logs).

## Benchmark Infrastructure

### Ranked Knowledge MCP
This project uses a custom Model Context Protocol (MCP) server for providing high-fidelity, grounded knowledge to AI agents during benchmarking. It features:
- **Ranked Retrieval:** Prioritizes high-value modules and symbols based on codebase structure.
- **Build-Time Bundling:** Performance-optimized indices bundled directly in the runner images.
- **Multi-Repo Support:** Can index and serve multiple target codebases simultaneously.

See [tools/adk_knowledge_ext/README.md](tools/adk_knowledge_ext/README.md) for setup details.

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
