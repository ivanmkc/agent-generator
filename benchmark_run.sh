#!/bin/bash
# Standard entry point for running ADK benchmarks.
# Usage: ./benchmark_run.sh <experiment_script.py> [args]

set -e

# Ensure we are in the project root
cd "$(dirname "$0")"

# Activate Env
source env/bin/activate

# Set Python Path to include root
export PYTHONPATH=.

# Run
python "$@"
