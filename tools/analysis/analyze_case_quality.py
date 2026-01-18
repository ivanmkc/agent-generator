import asyncio
import sqlite3
import json
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from google.genai import Client, types
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "benchmarks/analysis_cache.db"

QUALITY_AUDIT_PROMPT = """You are a Benchmark Quality Auditor.
Analyze the following failing benchmark case history to determine if the failure is likely due to a flaw in the BENCHMARK DEFINITION (ambiguous prompt, incorrect ground truth, unfair validation), or a flaw in the AGENT.

Benchmark Case: "{name}"
Recent Error: "{error}"
Explanation: "{explanation}"

Verdict options:
- BAD_CASE: Ambiguous Prompt
- BAD_CASE: Incorrect Ground Truth
- BAD_CASE: Unfair Validation
- GOOD_CASE: Agent Failure (Agent logic was wrong)
- UNCERTAIN: Need more info

Provide a short reasoning.

Response Format (JSON):
{{
  "verdict": "BAD_CASE" | "GOOD_CASE" | "UNCERTAIN",
  "issue": "Ambiguous Prompt" | "Incorrect Ground Truth" | ... | "Agent Logic",
  "reasoning": "..."
}}
"""

def get_top_failures(limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves top failing cases from the database."""
    if not Path(DB_PATH).exists():
        logger.error(f"Database not found at {DB_PATH}")
        return []

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # Group by benchmark_name and count failures
        cursor = conn.execute("""
            SELECT benchmark_name, COUNT(*) as fail_count, 
                   MAX(timestamp) as last_seen, 
                   raw_error, explanation
            FROM failures 
            GROUP BY benchmark_name 
            ORDER BY fail_count DESC 
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

async def audit_case(case: Dict[str, Any], model_name: str):
    """Uses LLM to audit the quality of a specific case."""
    prompt = QUALITY_AUDIT_PROMPT.format(
        name=case['benchmark_name'],
        error=case['raw_error'],
        explanation=case['explanation']
    )

    api_key = API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)
    if not api_key:
        logger.error("No API key available.")
        return None

    try:
        client = Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=[types.Content(parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return None

async def main(model_name: str):
    print("--- Benchmark Case Quality Auditor ---")
    logger.info(f"Using model: {model_name}")
    
    failures = get_top_failures(limit=5)
    
    if not failures:
        print("No failures found in database.")
        return

    print(f"Analyzing top {len(failures)} failing cases...\n")

    for case in failures:
        print(f"Case: {case['benchmark_name']}")
        print(f"  Failures: {case['fail_count']}")
        print(f"  Last Seen: {case['last_seen']}")
        
        result = await audit_case(case, model_name)
        if result:
            print(f"  [Audit Verdict]: {result.get('verdict')}")
            print(f"  [Issue]: {result.get('issue')}")
            print(f"  [Reasoning]: {result.get('reasoning')}")
        else:
            print("  [Audit]: Failed to analyze.")
        print("-" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Benchmark Case Quality")
    parser.add_argument("--model-name", required=True, help="LLM Model Name (e.g., gemini-2.0-flash-exp)")
    args = parser.parse_args()
    
    asyncio.run(main(args.model_name))
