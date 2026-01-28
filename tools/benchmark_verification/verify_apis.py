"""Verify Apis module."""

import yaml
import importlib
import sys
import os
from core.config import EXTRACTED_APIS_FILE, API_VERIFICATION_REPORT

INPUT_FILE = str(EXTRACTED_APIS_FILE)
OUTPUT_REPORT = str(API_VERIFICATION_REPORT)


def verify_api_existence(api_string):
    """
    Verifies if a fully qualified API string exists in the codebase.
    Tries to import the module and check for the attribute.
    """
    parts = api_string.split(".")
    if len(parts) < 2:
        return False, "Invalid format"

    # Try matching successively shorter module paths
    # e.g. google.adk.runners.InMemoryRunner
    # Try import google.adk.runners -> getattr InMemoryRunner
    # Try import google.adk.runners.InMemoryRunner (if it's a module)

    for i in range(len(parts), 0, -1):
        module_name = ".".join(parts[:i])
        attr_chain = parts[i:]

        try:
            module = importlib.import_module(module_name)
            # If we successfully imported the module, try to traverse attributes
            obj = module
            try:
                for attr in attr_chain:
                    obj = getattr(obj, attr)
                return True, "Found"
            except AttributeError:
                continue  # Try next split
        except ImportError:
            continue

    return False, "ImportError or AttributeError"


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r") as f:
        data = yaml.safe_load(f)

    print(f"Verifying {len(data)} APIs...")

    verified_results = []
    seen = set()

    for entry in data:
        api = entry["api_reference"]
        if api in seen:
            continue
        seen.add(api)

        exists, reason = verify_api_existence(api)

        verified_results.append(
            {
                "api": api,
                "exists": exists,
                "details": reason,
                "found_in_benchmarks": [
                    e["benchmark_file"] for e in data if e["api_reference"] == api
                ],
            }
        )

    # Filter for non-existent ones to highlight issues
    failures = [r for r in verified_results if not r["exists"]]

    print(
        f"Verification complete. Found {len(failures)} missing/invalid APIs out of {len(verified_results)} unique references."
    )

    with open(OUTPUT_REPORT, "w") as f:
        yaml.dump(
            {"failures": failures, "all_results": verified_results}, f, sort_keys=False
        )

    print(f"Report saved to {OUTPUT_REPORT}")


if __name__ == "__main__":
    # Ensure src is in python path if needed, though env/bin/python usually handles it
    # if installed in editable mode. If not, we might need to add PWD to path.
    sys.path.append(os.getcwd())
    sys.path.append(os.path.join(os.getcwd(), "src"))  # Try standard src dir
    # Also try repos/adk-python/src
    sys.path.append(os.path.join(os.getcwd(), "repos", "adk-python", "src"))

    main()
