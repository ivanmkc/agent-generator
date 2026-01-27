"""
Global Constants and File Paths.

This module defines the central configuration for file paths and directories used across
the project. It ensures that output directories exist and provides consistent access
to artifact locations.
"""

from pathlib import Path

# Project Root (calculated relative to tools/constants.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Centralized Output Directory
OUTPUT_ROOT = PROJECT_ROOT / "tmp/outputs"

# Sub-directories for specific artifacts
BENCHMARK_RUNS_DIR = OUTPUT_ROOT / "benchmark_runs"
GENERATED_BENCHMARKS_DIR = OUTPUT_ROOT / "generated_benchmarks"
REPORTS_DIR = OUTPUT_ROOT / "reports"

# Common File Paths
AGENTIC_SESSIONS_DB = OUTPUT_ROOT / "agentic_sessions.db"
AGENTIC_LOG_JSONL = OUTPUT_ROOT / "agentic_generated_raw.jsonl"
EXTRACTED_APIS_FILE = OUTPUT_ROOT / "extracted_apis_llm.yaml"
API_VERIFICATION_REPORT = OUTPUT_ROOT / "api_verification_report.yaml"
API_METADATA_FILE = OUTPUT_ROOT / "api_metadata.yaml"
VIBESHARE_RESULTS_FILE = OUTPUT_ROOT / "vibeshare_results.json"
RANKED_TARGETS_FILE = GENERATED_BENCHMARKS_DIR / "ranked_targets.yaml"
RANKED_TARGETS_MD = GENERATED_BENCHMARKS_DIR / "ranked_targets.md"


# Ensure dirs exist
def ensure_output_dirs():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    BENCHMARK_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# Call explicitly when importing if side-effects are desired, or let consumers call it.
ensure_output_dirs()
