#!/bin/bash

# Script to run the benchmark notebook via Papermill and save results to a unified directory.

# 1. Generate a shared timestamp/directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
# Ensure the path is relative to the project root or absolute
OUTPUT_DIR="benchmark_runs/$TIMESTAMP"
mkdir -p "$OUTPUT_DIR"

echo "Starting Benchmark Run..."
echo "Output Directory: $OUTPUT_DIR"

# 2. Convert Python script to Notebook
# We need to run the conversion script which is inside benchmarks/
# and expects benchmark_run.py in its CWD.
echo "Converting benchmark_run.py to notebook..."
(cd benchmarks && ../env/bin/python convert_py_to_ipynb.py benchmark_run.py)

# 3. Run papermill
# - Input: benchmarks/benchmark_run.ipynb (generated above)
# - Output: $OUTPUT_DIR/output.ipynb
# - Parameter 'run_output_dir_str': Passes the output directory to the notebook code
#   so traces and reports are saved in the same place.
env/bin/papermill benchmarks/benchmark_run.ipynb "$OUTPUT_DIR/output.ipynb" \
  --cwd . \
  -k python3 \
  -p run_output_dir_str "$OUTPUT_DIR"

echo "Benchmark execution complete."
echo "Results (Notebook, Traces, Reports) saved to: $OUTPUT_DIR"
