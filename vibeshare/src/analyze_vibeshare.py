"""
Main entry point for the VibeShare analysis pipeline.

This script orchestrates the two-phase analysis process:
1. Inference Phase: Runs prompts against models (cached).
2. Analysis Phase: Processes cached results to generate a structured JSON report.

Usage:
    python -m vibeshare.analyze_vibeshare
"""

import asyncio
import json
from asyncio import Semaphore
from config import MODELS, MAX_CONCURRENCY
from utils import load_prompts
from core import run_inference_task, create_vibeshare_result
from verify_models import run_verification

async def run_analysis():
    # Verify models first
    print("Verifying models...")
    working_models = await run_verification()
    
    if not working_models:
        print("No working models found. Aborting analysis.")
        return

    semaphore = Semaphore(MAX_CONCURRENCY)
    prompts_data = load_prompts()
    
    # Phase 1: Inference (Populate Cache)
    print(f"\n--- Phase 1: Running Inference (Caching) ---")
    print(f"Processing {len(prompts_data)} prompts on {len(working_models)} working models...")
    
    async with asyncio.TaskGroup() as tg:
        for prompt_item in prompts_data:
            for model in working_models:
                tg.create_task(run_inference_task(model, prompt_item, semaphore))
    
    # Phase 2: Analysis (Read Cache -> Generate Results)
    print(f"\n--- Phase 2: Generating Results from Cache ---")
    results_list = []
    
    for prompt_item in prompts_data:
        for model in working_models:
            result = create_vibeshare_result(model.model_name, prompt_item)
            results_list.append(result.to_dict())

    with open('vibeshare_results.json', 'w') as f:
        json.dump(results_list, f, indent=2)
    print(f"Analysis complete. Results saved to 'vibeshare_results.json'.")

if __name__ == "__main__":
    asyncio.run(run_analysis())
