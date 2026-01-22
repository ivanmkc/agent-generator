import os
import yaml
import re
import glob

# Configuration
BENCHMARK_ROOT = 'benchmarks/benchmark_definitions'
OUTPUT_FILE = 'extracted_apis.yaml'

# Regex for finding google.adk references
# Matches google.adk followed by word characters and dots.
# Example: google.adk.agents.BaseAgent
API_REGEX = re.compile(r'\bgoogle\.adk(?:\.[a-zA-Z0-9_]+)+\b')

def find_benchmark_files(root_dir):
    """Recursively find all benchmark.yaml files."""
    files = []
    for dirpath, _, filenames in os.walk(root_dir):
        if 'benchmark.yaml' in filenames:
            files.append(os.path.join(dirpath, 'benchmark.yaml'))
    return files

def extract_from_file(filepath):
    """Extract API references from a single benchmark file."""
    try:
        with open(filepath, 'r') as f:
            content = yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

    if not content or 'benchmarks' not in content:
        return []

    extracted = []
    
    for entry in content.get('benchmarks', []):
        case_id = entry.get('id', 'unknown')
        
        # 1. Explicit FQCNs (api_understanding)
        if 'answers' in entry:
            for ans in entry['answers']:
                fqcns = ans.get('fully_qualified_class_name', [])
                if isinstance(fqcns, list):
                    for fqcn in fqcns:
                        extracted.append({
                            'file': filepath,
                            'id': case_id,
                            'api': fqcn,
                            'source': 'fully_qualified_class_name'
                        })
                elif isinstance(fqcns, str):
                     extracted.append({
                        'file': filepath,
                        'id': case_id,
                        'api': fqcns,
                        'source': 'fully_qualified_class_name'
                    })

        # 2. Regex Scan in text fields
        text_fields = ['question', 'rationale', 'explanation', 'description']
        # Also scan options for MC
        if 'options' in entry:
            if isinstance(entry['options'], dict):
                text_fields.extend(entry['options'].values())
            elif isinstance(entry['options'], list):
                text_fields.extend(entry['options'])
        
        for field in text_fields:
            val = entry.get(field) if field in entry else field # Handle options values directly
            if isinstance(val, str):
                matches = API_REGEX.findall(val)
                for match in matches:
                    extracted.append({
                        'file': filepath,
                        'id': case_id,
                        'api': match,
                        'source': f"text_scan ({field if field in entry else 'option'})"
                    })

    return extracted

def main():
    files = find_benchmark_files(BENCHMARK_ROOT)
    print(f"Found {len(files)} benchmark files.")
    
    all_apis = []
    for f in files:
        print(f"Processing {f}...")
        apis = extract_from_file(f)
        all_apis.extend(apis)
    
    # Deduplicate slightly (same API in same ID/File)
    # But keep source info distinct if useful. 
    # For now, just dumping all.
    
    print(f"Extracted {len(all_apis)} potential API references.")
    
    with open(OUTPUT_FILE, 'w') as f:
        yaml.dump(all_apis, f, sort_keys=False)
    
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
