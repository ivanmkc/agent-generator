#!/bin/bash

# Script to run the benchmark via a pure Python script and save results to a unified directory.

# Ensure we are running from the project root
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT" || exit 1

# 1. Generate a shared timestamp/directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
# Use ADK_ARTIFACTS_DIR env var if set, otherwise default to ~/.agent_generator
# This allows multiple worktrees to share benchmark artifacts.
BASE_OUTPUT_DIR="${ADK_ARTIFACTS_DIR:-$HOME/.agent_generator}"
OUTPUT_DIR="$BASE_OUTPUT_DIR/benchmark_runs/$TIMESTAMP"
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
uv run python -u tools/cli/run_benchmarks.py "$@" 2>&1 | tee -a "$LOG_FILE"

# 4. Generate Visualization Report via Papermill
log "Generating visualization report..."
uv run python -m papermill tools/analysis/notebooks/benchmark_performance_summary.ipynb "$OUTPUT_DIR/benchmark_performance_summary.ipynb" \
  -p RUN_DIR "$OUTPUT_DIR" \
  --cwd . \
  -k case_quality \
  2>&1 | tee -a "$LOG_FILE"

log "Benchmark execution complete."
log "Results (JSON, Traces, Reports, Notebook) saved to: $OUTPUT_DIR"