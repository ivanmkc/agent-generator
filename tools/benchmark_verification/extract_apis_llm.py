"""Extract Apis Llm module."""

import os
import yaml
import re
from tools.constants import EXTRACTED_APIS_FILE, RANKED_TARGETS_FILE

# Configuration
BENCHMARK_ROOT = "benchmarks/benchmark_definitions"
RANKED_TARGETS_FILE = str(RANKED_TARGETS_FILE)
OUTPUT_FILE = str(EXTRACTED_APIS_FILE)


def load_ranked_targets(filepath):
    """Load ranked targets and return a set of valid API IDs."""
    try:
        with open(filepath, "r") as f:
            targets = yaml.safe_load(f)
            # Create a set of IDs (e.g., google.adk.runners.InMemoryRunner)
            return {t["id"] for t in targets if "id" in t}
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return set()


def find_benchmark_files(root_dir):
    """Recursively find all benchmark.yaml files."""
    files = []
    for dirpath, _, filenames in os.walk(root_dir):
        if "benchmark.yaml" in filenames:
            files.append(os.path.join(dirpath, "benchmark.yaml"))
    return files


def extract_apis_from_text(text, valid_apis):
    """
    Extract API references from text that match valid APIs.
    This simulates 'LLM extraction' by looking for known patterns
    that match the ranked targets.
    """
    found = []
    # Simple heuristic: Check if any valid API ID (or its last part) is present in the text
    # This is a proxy for "LLM extraction" where the LLM would identify symbols.
    # We prioritize longer matches (full FQCN) over shorter ones.

    # Check for full FQCNs first
    for api in valid_apis:
        if api in text:
            found.append(api)

    # Check for class names (e.g. "InMemoryRunner") if they are unique enough?
    # For now, let's stick to FQCNs or at least "google.adk..." patterns
    # and then try to match them to valid_apis.

    # Also find anything looking like a google.adk FQCN
    matches = re.findall(r"google\.adk\.[a-zA-Z0-9_\.]+", text)
    for m in matches:
        # cleanup trailing dots or non-word chars if regex grabbed too much
        m = m.rstrip(".")
        found.append(m)

    return list(set(found))


def process_benchmark_file(filepath, valid_apis):
    """Process a single benchmark file."""
    try:
        with open(filepath, "r") as f:
            content = yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

    if not content or "benchmarks" not in content:
        return []

    results = []
    for entry in content.get("benchmarks", []):
        case_id = entry.get("id", "unknown")

        # Combine all text fields to search in
        text_content = ""
        text_fields = ["question", "rationale", "explanation", "description"]
        if "options" in entry:
            if isinstance(entry["options"], dict):
                text_fields.extend(entry["options"].values())
            elif isinstance(entry["options"], list):
                text_fields.extend(entry["options"])

        for field in text_fields:
            val = entry.get(field) if field in entry else field
            if isinstance(val, str):
                text_content += val + " "

        # Also check answers for explicit FQCNs
        if "answers" in entry:
            for ans in entry["answers"]:
                fqcns = ans.get("fully_qualified_class_name", [])
                if isinstance(fqcns, list):
                    for f in fqcns:
                        text_content += f + " "
                elif isinstance(fqcns, str):
                    text_content += fqcns + " "

        extracted = extract_apis_from_text(text_content, valid_apis)

        for api in extracted:
            status = "matched" if api in valid_apis else "unmatched"
            results.append(
                {
                    "benchmark_file": filepath,
                    "case_id": case_id,
                    "api_reference": api,
                    "status": status,
                }
            )

    return results


def main():
    print(f"Loading ranked targets from {RANKED_TARGETS_FILE}...")
    valid_apis = load_ranked_targets(RANKED_TARGETS_FILE)
    print(f"Loaded {len(valid_apis)} valid API targets.")

    files = find_benchmark_files(BENCHMARK_ROOT)
    print(f"Found {len(files)} benchmark files.")

    all_extractions = []
    for f in files:
        print(f"Processing {f}...")
        extracted = process_benchmark_file(f, valid_apis)
        all_extractions.extend(extracted)

    print(f"Extracted {len(all_extractions)} references.")

    with open(OUTPUT_FILE, "w") as f:
        yaml.dump(all_extractions, f, sort_keys=False)

    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
