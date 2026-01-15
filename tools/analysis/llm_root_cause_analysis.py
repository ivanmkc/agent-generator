import asyncio
import json
import sqlite3
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Ensure root is in path
sys.path.append(os.getcwd())

from google.genai import types, Client
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "benchmarks/analysis_cache.db"
RUNS_DIR = Path("benchmark_runs")
MODEL_NAME = "gemini-2.0-flash-exp" 

# --- Prompts ---

ANALYSIS_PROMPT = """You are a rigorous Forensic Software Analyst auditing an autonomous agent's execution trace.

The agent failed to solve the benchmark: "{benchmark_name}"
Error: "{error_message}"

=== TRACE LOGS (JSONL Events) ===
{trace_json}
=================================

Your Goal: Determine the *exact* moment and reason the agent failed. Do not guess.

INSTRUCTIONS:
1. **Audit Tool Calls:** Scan the trace for every `tool_use` event.
   - Did the agent call the correct tool for the task?
   - Check `tool_input`: Were the arguments valid? (e.g. did it query a module that exists?)
   - Check `tool_output`: Did the tool return useful data (e.g. file content, search results) or an error/empty set?
   - *CRITICAL:* If the tool output was empty/insufficient, did the agent TRY AGAIN with a different tool (e.g. `search_files`), or did it just give up and guess?

2. **Audit Reasoning:** Look at the `model` messages/thoughts.
   - Did the agent acknowledge the tool outputs?
   - Did it hallucinate an API signature that contradicted the `read_file` or `get_module_help` output?
   - Did it verify its assumptions?

3. **Audit Output:** Check the final `tool_use` or response.
   - Did it match the required Pydantic schema (e.g., `FixErrorAnswerOutput`)?
   - Did it produce invalid JSON?

4. **Determine Root Cause:** Select the ONE category that best fits the *primary* failure.

Output valid JSON ONLY:
{{
  "root_cause_category": "Category",
  "explanation": "A precise, step-by-step narrative of the failure. Quote specific log events.",
  "evidence": [
    "Step 1: Agent called search_files('foo') -> Returned []",
    "Step 2: Agent ignored empty result and imported 'foo' anyway (Hallucination)"
  ],
  "tool_audit": {{
    "attempted_tools": ["list of tools called"],
    "successful_calls": true/false,
    "context_quality": "Good/Empty/Error"
  }}
}}

Categories:
- **Retrieval: Zero Results (Bad Query):** The agent called tools (e.g. `get_module_help`) with invalid arguments (e.g. non-existent module name) or keywords that yielded 0 results, and failed to correct the query.
- **Retrieval: Shallow (Missing Follow-up):** The agent retrieved *some* context (e.g. a top-level docstring), but it didn't contain the specific answer. The agent FAILED to pivot to `search_files` or deeper inspection to find the missing piece (Laziness).
- **Reasoning: Ignored Context (Hallucination):** The logs show the answer *was* present in the tool output (e.g. correct signature), but the agent's final answer CONTRADICTED it.
- **Reasoning: Fabrication (No Context):** The agent had *zero* relevant context (due to retrieval failure) and proceeded to invent/guess an answer anyway.
- **Output: Schema Violation:** The agent's logic/code was likely correct, but the final JSON output was malformed or missing required fields.
- **Output: Logic Error:** The agent wrote valid code that ran without crashing, but it failed the test assertions (wrong answer/logic).
- **Execution: Tool Misuse:** The agent failed to use tools correctly (syntax error) or skipped discovery entirely (jumped straight to coding).
- **Infrastructure:** System errors (429, 500, Timeout) unrelated to agent intelligence.
"""

# --- Database ---

def get_pending_failures():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT id, run_id, benchmark_name, attempt_number, raw_error 
            FROM failures 
            WHERE llm_root_cause IS NULL 
              AND run_id IN (
                  SELECT DISTINCT run_id 
                  FROM failures 
                  ORDER BY run_id DESC 
                  LIMIT 10
              )
              AND raw_error NOT LIKE '%429%'
              AND raw_error NOT LIKE '%ResourceExhausted%'
              AND raw_error NOT LIKE '%Quota%'
        """)
        return [dict(row) for row in cursor.fetchall()]

def update_failure(failure_id, analysis_json):
    try:
        data = json.loads(analysis_json)
        root_cause = data.get("root_cause_category", "Unknown")
    except:
        root_cause = "Analysis Failed"
        
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE failures 
            SET llm_analysis = ?, llm_root_cause = ?
            WHERE id = ?
        """, (analysis_json, root_cause, failure_id))
        conn.commit()

# --- Trace Extraction ---

def extract_trace(run_id, benchmark_name, attempt_number):
    log_file = RUNS_DIR / run_id / "trace.jsonl"
    if not log_file.exists():
        return None
    
    # Simple extraction: Find the test_result event for this benchmark
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            try:
                event = json.loads(line)
                if event.get("event_type") == "test_result":
                    data = event.get("data", {})
                    if data.get("benchmark_name") == benchmark_name:
                        attempts = data.get("generation_attempts", [])
                        for attempt in attempts:
                            if attempt.get("attempt_number") == attempt_number:
                                return attempt.get("trace_logs")
                        return data.get("trace_logs")
            except:
                continue
    return None

# --- LLM Client ---

async def analyze_with_llm(failure):
    failure_id = failure['id']
    run_id = failure['run_id']
    
    # 1. Get Trace
    trace_logs = await asyncio.to_thread(extract_trace, run_id, failure['benchmark_name'], failure['attempt_number'])
    
    if not trace_logs:
        logger.warning(f"Trace not found for {failure_id}")
        return

    # Truncate trace if too massive
    trace_str = json.dumps(trace_logs, indent=2)
    if len(trace_str) > 300000: 
        trace_str = trace_str[:150000] + "\n...[TRUNCATED]...\n" + trace_str[-150000:]

    prompt = ANALYSIS_PROMPT.format(
        benchmark_name=failure['benchmark_name'],
        error_message=failure['raw_error'],
        trace_json=trace_str
    )

    # 2. Retry Loop
    attempts = 0
    max_attempts = 3
    
    while attempts < max_attempts:
        attempts += 1
        
        api_key, key_id = API_KEY_MANAGER.get_next_key_with_id(KeyType.GEMINI_API)
        if not api_key:
            logger.warning("No API keys available, waiting...")
            await asyncio.sleep(5)
            continue

        try:
            client = Client(api_key=api_key)
            response = await client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            
            result_json = response.text
            # Simple validation
            json.loads(result_json) 
            
            # Report Success
            API_KEY_MANAGER.report_result(KeyType.GEMINI_API, key_id, True)
            
            await asyncio.to_thread(update_failure, failure_id, result_json)
            logger.info(f"Analyzed {failure_id}: Success")
            return

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Error analyzing {failure_id} (Attempt {attempts}/{max_attempts}): {error_msg}")
            
            # Report Failure
            API_KEY_MANAGER.report_result(KeyType.GEMINI_API, key_id, False, error_msg)
            
            # Backoff
            await asyncio.sleep(2 ** attempts)

    logger.error(f"Failed to analyze {failure_id} after {max_attempts} attempts.")

# --- Orchestrator ---

async def main():
    failures = await asyncio.to_thread(get_pending_failures)
    logger.info(f"Found {len(failures)} failures pending analysis.")
    
    # Increase concurrency slightly as we handle retries/backoff
    sem = asyncio.Semaphore(15)
    
    async def sem_task(failure):
        async with sem:
            await analyze_with_llm(failure)

    tasks = [sem_task(f) for f in failures]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())