import asyncio
import logging
import sys
from pathlib import Path
from benchmarks.data_models import BenchmarkRunResult

# Setup path and imports
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from tools.analysis.case_summarizer import CASE_DOC_MANAGER, SUMMARY_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_one_liner_generation():
    # Example data simulating a CaseAnalysis object
    case_name = "configure_adk_features_mc:how_do_you_enable_codeexecutiontool_via_configurat"
    
    # This is the actual question text from the yaml we cat'd earlier
    prompt_text = "How do you enable `CodeExecutionTool` via configuration?" 
    
    model_name = "gemini-2.0-flash"

    print(f"\n--- Testing One-Liner Generation for {case_name} ---")
    print(f"Input Prompt Text:\n{prompt_text}\n")
    print(f"Instruction Prompt Template:\n{SUMMARY_PROMPT}\n")

    # Force regeneration by clearing any potential cache entry for this specific test (optional, but good for demo)
    # CASE_DOC_MANAGER._update_cache(case_name, "dummy", "checksum") # Not needed if we trust the manager logic

    one_liner = await CASE_DOC_MANAGER.get_one_liner(case_name, prompt_text, model_name)
    
    print(f"Generated One-Liner Output:\n{one_liner}\n")

if __name__ == "__main__":
    asyncio.run(test_one_liner_generation())

