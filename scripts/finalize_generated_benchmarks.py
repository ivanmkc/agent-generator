import json
import yaml
import os
from pathlib import Path

def finalize_benchmarks():
    raw_path = Path("agentic_generated_raw.jsonl")
    output_dir = Path("benchmarks/benchmark_definitions/agentic_generated")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not raw_path.exists():
        print("No raw benchmarks found.")
        return

    count = 0
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                
                # Map to ADK Benchmark YAML Schema
                yaml_data = {
                    "metadata": {
                        "id": f"agentic_{count}",
                        "target_id": data.get("target_id"),
                        "type": "multiple_choice",
                        "source": "agentic_generator"
                    },
                    "prompts": [{
                        "q": data.get("question"),
                        "options": [
                            opt["code"] if isinstance(opt, dict) else str(opt) 
                            for opt in data.get("options", [])
                        ],
                        "a": data.get("correct_option_id", "correct_implementation")
                    }]
                }
                
                # Fix options if they are dicts (Agentic output) vs list of strings (Benchmark Runner expectation)
                # The Agentic output has options with descriptions. We need to format them for the runner.
                # Runner expects list of strings usually? Or does it support objects?
                # Looking at standard format: usually just strings.
                # But Agentic generates code blocks.
                
                # Let's clean up options.
                # Identify index of correct option
                options_list = data.get("options", [])
                correct_id = data.get("correct_option_id")
                correct_idx = 0
                
                formatted_options = []
                for idx, opt in enumerate(options_list):
                    code = opt.get("code", "") if isinstance(opt, dict) else str(opt)
                    formatted_options.append(code)
                    if isinstance(opt, dict) and opt.get("id") == correct_id:
                        correct_idx = idx
                
                yaml_data["prompts"][0]["options"] = formatted_options
                yaml_data["prompts"][0]["a"] = str(correct_idx) # Index of correct answer
                
                # Save
                file_name = f"benchmark_{count}.yaml"
                with open(output_dir / file_name, "w") as out:
                    yaml.dump(yaml_data, out, sort_keys=False)
                
                count += 1
            except Exception as e:
                print(f"Skipping line {count}: {e}")

    print(f"Converted {count} benchmarks to YAML in {output_dir}")

if __name__ == "__main__":
    finalize_benchmarks()
