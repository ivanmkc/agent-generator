# Diagnose Setup Errors (Multiple Choice) Benchmark

This benchmark evaluates the model's ability to diagnose common setup and configuration errors in the ADK through a series of multiple-choice questions.

## `benchmark.yaml`

This file defines the multiple-choice questions. Each question presents a scenario with a setup error and asks the model to identify the cause. Each question includes:
- A description of the error scenario.
- A set of options explaining the possible cause.
- The correct answer.

## `verify_diagnose.py`

This script validates the integrity of `benchmark.yaml`, ensuring that it is well-formed and that all questions have a correct answer.
