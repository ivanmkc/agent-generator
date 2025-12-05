# Predict Runtime Behavior (Multiple Choice) Benchmark

This benchmark evaluates the model's ability to predict the runtime behavior of ADK code snippets through a series of multiple-choice questions.

## `benchmark.yaml`

This file defines the multiple-choice questions. Each question presents a code snippet and asks the model to predict its output or behavior. Each question includes:
- A code snippet.
- A set of options describing the possible outcomes.
- The correct answer.

## `verify_predict.py`

This is a **verification script** that validates the *structural integrity* of `benchmark.yaml` and its associated code snippets. It checks whether the YAML file is well-formed, if all referenced code snippet files exist, if the snippets are correctly formatted with their tags, and if all questions have valid options and a correct answer. Crucially, it **does not execute** the code snippets; its role is solely to ensure the benchmark definition is well-formed and consistent.

## `test_code_predictions.py`

This is a **pytest test file** that *executes* the code snippets referenced in `benchmark.yaml`. Its primary purpose is to **verify the accuracy of the predictions** by running each code snippet and comparing its actual output or behavior against the expected correct answer specified in the benchmark definition. It ensures that the benchmarks themselves are functionally correct and that the code snippets produce the outcomes they claim.

## `snippets/`

This directory contains Python files with tagged code snippets that are referenced by the benchmark cases. This allows for clean separation of code and test definitions.
