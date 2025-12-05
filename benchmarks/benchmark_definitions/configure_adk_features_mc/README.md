# ADK Features (Multiple Choice) Benchmark

This benchmark evaluates the model's knowledge of ADK features and configuration options through a series of multiple-choice questions.

## `benchmark.yaml`

This file defines the multiple-choice questions. Each question includes:
- A question about a specific ADK feature or configuration.
- A set of options.
- The correct answer.

## `verify_configure.py`

This script validates the integrity of `benchmark.yaml`, ensuring that it is well-formed and that all questions have a correct answer.
