#!/bin/bash

# Script to run the benchmark notebook via Papermill and save results to a unified directory.

# 1. Generate a shared timestamp/directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
# Ensure the path is relative to the project root or absolute
OUTPUT_DIR="benchmark_runs/$TIMESTAMP"
mkdir -p "$OUTPUT_DIR"

echo "Starting Benchmark Run..."
echo "Output Directory: $OUTPUT_DIR"

# 2. Run papermill
# - Input: benchmark_run.ipynb
# - Output: $OUTPUT_DIR/output.ipynb
# - Parameter 'run_output_dir_str': Passes the output directory to the notebook code
#   so traces and reports are saved in the same place.
env/bin/papermill benchmark_run.ipynb "$OUTPUT_DIR/output.ipynb" \
  --cwd . \
  -k python3 \
  -p run_output_dir_str "$OUTPUT_DIR"

echo "Benchmark execution complete."
echo "Results (Notebook, Traces, Reports) saved to: $OUTPUT_DIR"
