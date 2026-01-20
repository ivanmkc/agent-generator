
import yaml
import sys
from pathlib import Path
from collections import defaultdict

def analyze_chunked_logs(log_file):
    print(f"Analyzing logs from: {log_file}")
    
    # Structure: results[benchmark_name][generator_name] = {status, tokens, duration, ...}
    results = defaultdict(dict)
    
    current_benchmark = None
    current_generator = None
    
    try:
        with open(log_file, 'r') as f:
            # Use yaml.safe_load_all to parse the multi-document YAML stream
            for event in yaml.safe_load_all(f):
                if event is None:
                    continue
                evt_type = event.get("event_type")
                data = event.get("data", {})
                
                if evt_type == "section_start":
                    name = data.get("name", "")
                    if name.startswith("Agent: "):
                        current_generator = name.replace("Agent: ", "")
                        
                elif evt_type == "test_result":
                    bench_name = data.get("benchmark_name")
                    if bench_name and current_generator:
                        # Extract usage from the test result if available
                        usage = data.get("usage_metadata") or {}
                        
                        # If usage is not directly in data (sometimes in generation_attempts)
                        if not usage:
                            attempts = data.get("generation_attempts") or []
                            if attempts:
                                total_tokens = sum((a.get("usage_metadata") or {}).get("total_tokens", 0) for a in attempts)
                                prompt_tokens = sum((a.get("usage_metadata") or {}).get("prompt_tokens", 0) for a in attempts)
                                completion_tokens = sum((a.get("usage_metadata") or {}).get("completion_tokens", 0) for a in attempts)
                                usage = {
                                    "total_tokens": total_tokens,
                                    "prompt_tokens": prompt_tokens,
                                    "completion_tokens": completion_tokens
                                }

                        results[bench_name][current_generator] = {
                            "result": data.get("result"),
                            "status": data.get("status") or ("PASS" if data.get("result") == "pass" else "FAIL"), # Normalize
                            "duration": 0.0, # Placeholder
                            "tokens": usage.get("total_tokens", 0),
                            "prompt": usage.get("prompt_tokens", 0),
                            "completion": usage.get("completion_tokens", 0)
                        }
                        
                        # Look for duration in generation_attempts if available
                        attempts = data.get("generation_attempts") or []
                        if attempts:
                            total_duration = sum(a.get("duration", 0) for a in attempts)
                            results[bench_name][current_generator]["duration"] = total_duration

    except FileNotFoundError:
        print("Log file not found.")
        return
    except Exception as e:
        print(f"Error parsing YAML: {e}")
        return

    # Print Comparison Table
    print("\n" + "="*120)
    print(f"{ 'Benchmark Case':<50} | { 'Generator':<40} | { 'Status':<10} | { 'Tokens':<10} | { 'Time (s)':<10}")
    print("="*120)
    
    for bench_name, gen_data in results.items():
        first = True
        for gen_name, stats in gen_data.items():
            bench_str = bench_name[:48] + ".." if len(bench_name) > 48 else bench_name
            if not first:
                bench_str = "" 
            
            status = stats["result"] # Raw result string like 'fail_generation'
            tokens = stats["tokens"]
            duration = f"{stats['duration']:.2f}"
            
            print(f"{bench_str:<50} | {gen_name:<40} | {status:<10} | {tokens:<10} | {duration:<10}")
            first = False
        print("-" * 120)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_benchmark_chunks.py <path_to_trace.yaml>")
        sys.exit(1)
        
    analyze_chunked_logs(sys.argv[1])
