import sys
import time
import os
import streamlit as st
import pandas as pd
from pathlib import Path

# Add project root to sys.path
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.append(root_dir)
# Add tools/viewer to sys.path to import view_benchmarks
sys.path.append(os.path.join(root_dir, "tools", "viewer"))

try:
    import view_benchmarks
except ImportError as e:
    print(f"Failed to import view_benchmarks: {e}")
    sys.exit(1)

def main():
    print("Starting headless profiling of viewer data loading...")
    
    # 1. Load Run Options
    print("\n--- Profiling load_run_options ---")
    start = time.perf_counter()
    try:
        runs = view_benchmarks.load_run_options()
    except Exception as e:
        print(f"Error loading runs: {e}")
        return
    end = time.perf_counter()
    print(f"Time: {end - start:.4f}s")
    print(f"Found {len(runs)} runs.")

    if not runs:
        print("No runs found. Exiting.")
        return

    # Select the first run (latest)
    # runs is a list of dicts: {'id': '...', 'status': '...'}
    selected_run_obj = runs[0]
    selected_run_id = selected_run_obj["id"]
    print(f"\nSelected latest run: {selected_run_id}")

    # 2. Load Results
    print(f"\n--- Profiling load_results('{selected_run_id}') ---")
    start = time.perf_counter()
    try:
        results_list = view_benchmarks.load_results(selected_run_id)
    except Exception as e:
        print(f"Error loading results: {e}")
        return
    end = time.perf_counter()
    print(f"Time: {end - start:.4f}s")
    print(f"Loaded {len(results_list)} results.")

    if not results_list:
        print("No results loaded. Exiting.")
        return

    # 3. Create DataFrame
    print("\n--- Profiling DataFrame Creation ---")
    start = time.perf_counter()
    try:
        df = pd.DataFrame([r.model_dump(mode="json") for r in results_list])

        if "suite" in df.columns:
            df["suite"] = df["suite"].apply(
                lambda x: Path(x).parent.name if "/" in x else x
            )
    except Exception as e:
        print(f"Error creating DataFrame: {e}")
        return
    end = time.perf_counter()
    print(f"Time: {end - start:.4f}s")
    print(f"DataFrame shape: {df.shape}")

    # 4. Filter Data (optional simulation)
    print("\n--- Profiling Filter Data (No-op copy) ---")
    start = time.perf_counter()
    filtered_df = df.copy()
    end = time.perf_counter()
    print(f"Time: {end - start:.4f}s")

    print("\nProfiling complete.")

if __name__ == "__main__":
    main()
