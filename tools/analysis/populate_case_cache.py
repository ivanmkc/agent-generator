import asyncio
import yaml
from pathlib import Path
import logging
import hashlib
from typing import List

# Setup path to allow imports from project root
import sys
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tools.analysis.case_summarizer import CASE_DOC_MANAGER, CaseDocCache, CaseDocEntry

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def populate_cache():
    benchmark_defs_dir = project_root / "benchmarks" / "benchmark_definitions"
    yaml_files = list(benchmark_defs_dir.glob("**/benchmark.yaml"))
    
    logger.info(f"Found {len(yaml_files)} benchmark definition files.")
    
    model_name = "gemini-2.0-flash"
    
    for yaml_file in yaml_files:
        logger.info(f"Processing {yaml_file.relative_to(project_root)}")
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            benchmarks = data.get("benchmarks", [])
            for case in benchmarks:
                case_id = case.get("id")
                if not case_id:
                    continue
                
                # Determine the core text to summarize
                # For mc and api_understanding, it's 'question'
                # For fix_error, it's 'description' or sometimes 'prompt'
                prompt_text = case.get("question") or case.get("description") or case.get("prompt")
                
                if not prompt_text:
                    logger.warning(f"No prompt text found for case {case_id}")
                    continue
                
                # Use CASE_DOC_MANAGER to get one-liner (will handle caching and checksums)
                one_liner = await CASE_DOC_MANAGER.get_one_liner(case_id, prompt_text, model_name)
                # logger.info(f"  [{case_id}] -> {one_liner}")
                
        except Exception as e:
            logger.error(f"Failed to process {yaml_file}: {e}")

if __name__ == "__main__":
    asyncio.run(populate_cache())
