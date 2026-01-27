# Ground Truth Answer Generator

## Core Philosophy
A "perfect" generator that extracts the known correct answer directly from the benchmark case. Used to verify the upper bound of the benchmark harness and validate the scoring logic.

## Topology
Oracle Generator

## Architecture Overview
The Ground Truth generator introspects the `BenchmarkCase` object to find the `ground_truth` or `correct_answer` field. It then packages this data into the expected `GeneratedAnswer` format. If the benchmark runner fails when using this generator, it indicates a bug in the verification logic (pytest, signature check, etc.) rather than the model.
