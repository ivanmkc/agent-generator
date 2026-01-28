#!/bin/bash

# Script to run the benchmark via a pure Python script and save results to a unified directory.

# Ensure we are running from the project root
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT" || exit 1

# 1. Generate a shared timestamp/directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
OUTPUT_DIR="tmp/outputs/benchmark_runs/$TIMESTAMP"
mkdir -p "$OUTPUT_DIR"
LOG_FILE="$OUTPUT_DIR/benchmark_run.log"

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting Benchmark Run..."
log "Output Directory: $OUTPUT_DIR"

# 2. Export the output directory so the Python script can read it
export BENCHMARK_OUTPUT_DIR="$OUTPUT_DIR"
# Ensure we use the right python and project root in path
export PYTHONPATH=$PYTHONPATH:.

# 3. Run the Python benchmark script directly
log "Running Python benchmark script..."
python3 -u tools/cli/run_benchmarks.py "$@" 2>&1 | tee -a "$LOG_FILE"

# 4. Generate Visualization Report via Papermill
log "Generating visualization report..."
python3 -m papermill tools/analysis/notebooks/benchmark_performance_summary.ipynb "$OUTPUT_DIR/benchmark_performance_summary.ipynb" \
  -p RUN_DIR "$OUTPUT_DIR" \
  --cwd . \
  -k python3 \
  2>&1 | tee -a "$LOG_FILE"

log "Benchmark execution complete."
log "Results (JSON, Traces, Reports, Notebook) saved to: $OUTPUT_DIR"