import yaml
from pathlib import Path
from typing import List, Dict

def load_prompts() -> List[Dict[str, str]]:
    """
    Loads prompts from prompts.yaml.
    Structure:
    category_name:
      - prompt 1
    """
    # Assuming prompts.yaml is in the parent directory of this file (vibeshare/)
    prompts_path = Path(__file__).parent / "prompts.yaml"
    with open(prompts_path, "r") as f:
        data = yaml.safe_load(f)
    
    all_prompts = []
    if isinstance(data, dict):
        for category, prompts in data.items():
            if isinstance(prompts, list):
                for p in prompts:
                    all_prompts.append({"category": category, "prompt": p})
    return all_prompts
