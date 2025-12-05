# API Understanding Benchmark

This benchmark evaluates the model's ability to understand and answer questions about the ADK's public API.

## `benchmark.yaml`

This file defines the benchmark cases. Each case includes:
- A question about the ADK API.
- The expected code snippet as an answer.
- Metadata for validation, such as the template for the expected answer.

## `verify_api_understanding.py`

This script validates the integrity of `benchmark.yaml`, ensuring that it is well-formed and that all referenced files and templates are valid.

## `snippets/`

This directory contains Python files with tagged code snippets that are referenced by the benchmark cases. This allows for clean separation of code and test definitions.
