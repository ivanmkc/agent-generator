"""
CLI tool to verify benchmark quality using the VerifierAgent.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import traceback
import re
try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    # Fallback if colorama not present
    class MockColor:
        def __getattr__(self, name): return ""
    Fore = Style = MockColor()

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from benchmarks.answer_generators.verifier_pipeline import create_verifier_adk_generator
from core.api_key_manager import ApiKeyManager, KeyType
from benchmarks.answer_generators.adk_context import adk_execution_context
from core.config import DATA_DIR, PROJECT_ROOT, MOST_POWERFUL_MODEL, OUTPUT_ROOT
from dotenv import load_dotenv
load_dotenv()
try:
    import yaml
except ImportError:
    print("Error: PyYAML is not installed. Please install it.")
    sys.exit(1)

def print_verification_details(logs: List[Any]):
    """
    Parses trace logs to print detailed, colored information about Claims and Tests.
    """
    print(f"\n{Style.BRIGHT}{Fore.CYAN}=== Detailed Verification Log ==={Style.RESET_ALL}")
    
    for event in logs:
        # 1. Capture Claims from ClaimAnalyst
        if getattr(event, 'author', '') == 'claim_analyst' and getattr(event, 'role', '') == 'model':
            content = getattr(event, 'content', '')
            if content is None:
                continue
            if not isinstance(content, str):
                content = str(content)
                
            # Look for JSON block
            match = re.search(r"```json\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
            if match:
                print(f"\n{Fore.YELLOW}[Claim Analyst] Generated Claims:{Style.RESET_ALL}")
                try:
                    # Parse and re-dump to pretty print, or just print raw if parsing fails
                    claims = json.loads(match.group(1))
                    print(json.dumps(claims, indent=2))
                except:
                    print(match.group(1))
            else:
                # If no JSON block, just print content (might be rationale)
                print(f"\n{Fore.YELLOW}[Claim Analyst] Thought Process:{Style.RESET_ALL}")
                print(content.strip())

        # 2. Capture Pytest executions from ProofEngineer
        if getattr(event, 'type', '') == 'tool_use' and getattr(event, 'tool_name', '') == 'run_shell_command':
             tool_input = getattr(event, 'tool_input', {})
             # Debug print
             print(f"DEBUG: run_shell_command input: {tool_input}")
             
             cmd = tool_input.get('command', '')
             desc = tool_input.get('description', '')
             if 'pytest' in cmd:
                 print(f"\n{Fore.BLUE}[Proof Engineer] Running Test:{Style.RESET_ALL} {Style.BRIGHT}{cmd}{Style.RESET_ALL}")
                 if desc:
                     print(f"{Fore.BLUE}  Goal:{Style.RESET_ALL} {desc}")

        if getattr(event, 'type', '') == 'tool_result' and getattr(event, 'tool_name', '') == 'run_shell_command':
            # We assume this result follows the pytest command above. 
            # (In a strict async stream we'd match IDs, but sequential logs work here)
            output = getattr(event, 'tool_output', '')
            if "=== test session starts ===" in output or "collected" in output:
                # It's likely pytest output
                print(f"{Fore.BLUE}[Proof Engineer] Test Output:{Style.RESET_ALL}")
                
                # Colorize Pass/Fail
                if " failed," in output or " error," in output or "FAILED" in output:
                    color = Fore.RED
                elif " passed" in output or "PASSED" in output:
                    color = Fore.GREEN
                else:
                    color = Fore.WHITE
                
                print(f"{color}{output}{Style.RESET_ALL}")

    print(f"{Style.BRIGHT}{Fore.CYAN}==================================={Style.RESET_ALL}\n")

import shutil
import datetime as _dt

# ... imports ...


async def verify_benchmark(
    benchmark_file: Path,
    run_dir: Path,
    model_name: str,
    api_key_manager: ApiKeyManager,
    skip_ids: Optional[set] = None,
    repo_url: str = "https://github.com/google/adk-python.git",
    repo_version: str = "v1.20.0",
    setup_cmd: Optional[List[str]] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
    max_retries: int = 3,
    min_wait: float = 2.0,
    max_wait: float = 60.0
):
    """Verifies a single benchmark file using concurrency across cases."""
    if skip_ids is None:
        skip_ids = set()
    if semaphore is None:
        semaphore = asyncio.Semaphore(1)

    try:
        rel_path = benchmark_file.relative_to(PROJECT_ROOT)
    except ValueError:
        rel_path = benchmark_file
        
    print(f"\n{Style.BRIGHT}{Fore.CYAN}=== Scanning {rel_path} ==={Style.RESET_ALL}")
    
    try:
        with open(benchmark_file, 'r') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML {benchmark_file}: {e}")
        return
        
    benchmarks = data.get('benchmarks', [])
    if not benchmarks:
        print("No benchmarks found in file.")
        return

    # Extract sandbox config if it exists at root level of benchmark.yaml
    yaml_target_repo = data.get("target_repo_url", repo_url)
    yaml_target_version = data.get("target_repo_version", repo_version)
    yaml_extra_deps = data.get("extra_dependencies", setup_cmd)
    
    # We map benchmark_type globally to the file since the factory needs it
    benchmark_type = data.get("benchmarks", [{}])[0].get("benchmark_type", "multiple_choice")

    async def _process_case(case):
        case_id = case.get('id')
        if case_id in skip_ids:
            return None

        slug = re.sub(r'[^a-zA-Z0-9_]', '_', case_id)
        case_output_dir = run_dir / slug
        
        async with semaphore:
            case_output_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n  {Style.BRIGHT}{Fore.BLUE}▶ Verifying Case: {case_id}{Style.RESET_ALL}")
            print(f"    {Fore.LIGHTBLACK_EX}Artifacts: {case_output_dir}{Style.RESET_ALL}")
            
            for attempt_idx in range(max_retries + 1):
                generator = create_verifier_adk_generator(
                    model_name=model_name, 
                    api_key_manager=api_key_manager,
                    benchmark_type=benchmark_type,
                    target_repo_url=yaml_target_repo,
                    target_repo_version=yaml_target_version,
                    extra_dependencies=yaml_extra_deps
                )
                
                token = None
                try:
                    import time
                    t_setup_start = time.time()
                    await generator.setup()
                    t_setup_end = time.time()
                    setup_time = t_setup_end - t_setup_start
                    
                    if api_key_manager:
                        run_id = f"verifier_{case_id}_{attempt_idx}"
                        current_key, api_key_id = await api_key_manager.get_key_for_run(run_id, KeyType.GEMINI_API)
                        token = adk_execution_context.set({"api_key": current_key, "key_id": api_key_id})
                    
                    prompt = f"""
                    Task: Verify this Benchmark Question. 
                    
                    Question ID: {case_id}
                    Question: {case.get('question')}
                    Options: {json.dumps(case.get('options', {}), indent=2)}
                    
                    Ground Truth (Hidden from Analyst, used for final grading): {case.get('correct_answer')}
                    Explanation: {case.get('explanation')}
                    
                    Please execute the verification workflow:
                    1. Research the codebase.
                    2. Decompose options into claims.
                    3. Prove each claim with code.
                    4. Provide a verdict: Valid, Ambiguous, or Incorrect.
                    """
                    
                    t_llm_start = time.time()
                    response, trace_logs, usage_metadata, _ = await asyncio.wait_for(
                        generator._run_agent_async(prompt, benchmark_type="verification"), 
                        timeout=600
                    )
                    t_llm_end = time.time()
                    agent_exec_time = t_llm_end - t_llm_start
                    
                    print_verification_details(trace_logs)
                    
                    workspace_dir = None
                    claims = []
                    for event in trace_logs:
                        author = getattr(event, 'author', '')
                        content = getattr(event, 'content', '')
                        if not content: continue
                        if author == 'setup_agent' and '"workspace_dir"' in str(content):
                            try:
                                clean_content = content
                                if "said: " in content:
                                    clean_content = content.split("said: ", 1)[1]
                                data2 = json.loads(clean_content)
                                if isinstance(data2, dict) and "workspace_dir" in data2:
                                    workspace_dir = Path(data2["workspace_dir"])
                            except:
                                match2 = re.search(r'"workspace_dir":\s*"([^"]+)"', str(content))
                                if match2:
                                    workspace_dir = Path(match2.group(1).replace('\\\\', '\\'))
                        if author == 'claim_analyst' and '"option"' in str(content):
                            try:
                                match2 = re.search(r"```json\s*([\s\S]*?)\s*```", str(content), re.IGNORECASE)
                                if match2:
                                    claims = json.loads(match2.group(1))
                            except:
                                pass
                    
                    if workspace_dir and workspace_dir.exists():
                        artifacts_dir = case_output_dir / "workspace_files"
                        artifacts_dir.mkdir(exist_ok=True)
                        found_files = 0
                        for source_dir in [workspace_dir]:
                            if not source_dir.exists(): continue
                            for file_path in source_dir.glob("*"):
                                if file_path.is_file() and file_path.suffix in ['.py', '.txt', '.md', '.json', '.log']:
                                    if "venv" in str(file_path): continue
                                    try:
                                        shutil.copy2(file_path, artifacts_dir)
                                        found_files += 1
                                    except Exception:
                                        pass
                    
                    with open(case_output_dir / f"trace_logs_attempt_{attempt_idx}.json", "w") as f2:
                        json.dump([e.model_dump(mode='json') for e in trace_logs], f2, indent=2)

                    from google import genai
                    from google.genai import types
                    from benchmarks.answer_generators.verifier_pipeline.models import VerificationVerdict

                    t_fmt_start = time.time()

                    try:
                        # Grab the current key if we used one or default to the environment
                        api_key_to_use = current_key if getattr(locals(), 'current_key', None) else os.environ.get("GEMINI_API_KEY")
                        
                        client = genai.Client(api_key=api_key_to_use)
                        formatting_prompt = f"Extract the final verification verdict and details from this unstructured text (if it's already JSON, just conform it exactly to the schema):\n\n{response}"

                        formatter_result = await asyncio.to_thread(
                            client.models.generate_content,
                            model=model_name,
                            contents=formatting_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=VerificationVerdict,
                                temperature=0.0
                            )
                        )
                        details = json.loads(formatter_result.text)
                        verdict = details.get("verdict", "Unknown")
                    except Exception as e:
                        print(f"    {Fore.RED}Formatter failed: {e}{Style.RESET_ALL}")
                        details = {}
                        verdict = "Unknown"
                        
                    # Fallback to regex safely if the formatting call completely fails
                    if verdict == "Unknown":
                        if re.search(r"Verdict:\s*Valid", response, re.IGNORECASE): verdict = "Valid"
                        elif re.search(r"Verdict:\s*Ambiguous", response, re.IGNORECASE): verdict = "Ambiguous"
                        elif re.search(r"Verdict:\s*Incorrect", response, re.IGNORECASE): verdict = "Incorrect"

                    t_fmt_end = time.time()
                    format_time = t_fmt_end - t_fmt_start

                    v_color = Fore.GREEN if verdict == "Valid" else Fore.RED if verdict == "Incorrect" else Fore.YELLOW if verdict == "Ambiguous" else Fore.WHITE
                    v_icon = "✅" if verdict == "Valid" else "❌" if verdict == "Incorrect" else "⚠️" if verdict == "Ambiguous" else "❓"
                    print(f"    {Style.BRIGHT}{v_color}{v_icon} Verdict: {verdict}{Style.RESET_ALL}")
                    
                    if api_key_manager and api_key_id:
                        await api_key_manager.report_result(
                            KeyType.GEMINI_API, api_key_id, success=True
                        )
                    
                    case_result = {
                        "id": case_id,
                        "verdict": verdict,
                        "question": case.get("question"),
                        "expected_answer": case.get("correct_answer"),
                        "options": case.get("options", {}),
                        "details": details,
                        "claims": claims,
                        "full_response": response,
                        "tokens": usage_metadata.total_tokens if usage_metadata else 0,
                        "artifact_path": str(case_output_dir),
                        "attempts": attempt_idx + 1,
                        "profiling": {
                            "setup_sec": round(setup_time, 2),
                            "agent_exec_sec": round(agent_exec_time, 2),
                            "format_sec": round(format_time, 2),
                            "total_sec": round(setup_time + agent_exec_time + format_time, 2)
                        }
                    }
                    
                    with open(case_output_dir / "report.json", "w") as f2:
                        json.dump(case_result, f2, indent=2)
                    return case_result

                except Exception as e:
                    should_retry = attempt_idx < max_retries
                    
                    if api_key_manager and api_key_id:
                        await api_key_manager.report_result(
                            KeyType.GEMINI_API,
                            api_key_id,
                            success=False,
                            error_message=str(e)
                        )

                    if token:
                        adk_execution_context.reset(token)
                        if api_key_manager:
                            try:
                                api_key_manager.release_run(f"verifier_{case_id}_{attempt_idx}")
                            except:
                                pass
                    await generator.teardown()
                    
                    if should_retry:
                        import random
                        # Exponential backoff: min_wait * 2^attempt
                        delay = min(max_wait, min_wait * (2**attempt_idx))
                        # Add jitter (0.5 to 1.5 multiplier)
                        delay *= 0.5 + random.random()
                        print(f"      {Fore.YELLOW}↻ Retrying Case {case_id} in {delay:.1f}s (Attempt {attempt_idx+1}/{max_retries}){Style.RESET_ALL} - {str(e)[:100]}")
                        await asyncio.sleep(delay)
                    else:
                        print(f"      {Fore.RED}❌ Error checking case {case_id} after {attempt_idx+1} attempts: {e}{Style.RESET_ALL}")
                        traceback.print_exc()
                        res = {
                            "id": case_id,
                            "verdict": "Error",
                            "error": str(e),
                            "question": case.get("question"),
                            "options": case.get("options", {}),
                            "expected_answer": case.get("correct_answer"),
                            "attempts": attempt_idx + 1
                        }
                        with open(case_output_dir / "report.json", "w") as f2:
                            json.dump(res, f2, indent=2)
                        return res

    # execute all cases in THIS file asynchronously
    tasks = [_process_case(case) for case in benchmarks]
    raw_results = await asyncio.gather(*tasks)
    return [r for r in raw_results if r]

async def main():
    parser = argparse.ArgumentParser(description="Verify benchmark quality.")
    parser.add_argument("--model", default=MOST_POWERFUL_MODEL, help="Model to use (ignored, using strongest model).")
    parser.add_argument("--target", help="Specific benchmark file or directory.")
    parser.add_argument("--suite-filter", help="Substring filter for benchmark suites (e.g., 'mc', 'fix_errors').")
    parser.add_argument("--resume-from", help="Resume from a specific run directory.")
    parser.add_argument("--resume-latest", action="store_true", help="Resume from the most recent run directory.")
    
    # Generic Repository Sandboxing Settings
    parser.add_argument("--repo-url", help="Target repository URL for the code context", default="https://github.com/google/adk-python.git")
    parser.add_argument("--repo-version", help="Version/Branch of the target repository", default="v1.20.0")
    parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent verify cases.")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum number of retries per case.")
    parser.add_argument("--min-wait", type=float, default=2.0, help="Minimum wait time between retries in seconds.")
    parser.add_argument("--max-wait", type=float, default=60.0, help="Maximum wait time between retries in seconds.")
    parser.add_argument("--extra-dep", action="append", help="Extra dependency constraints to inject into the sandbox pyproject.toml before uv sync (e.g. 'django>=4.0'). Passed multiple times for multiple packages.")
    
    args = parser.parse_args()
    
    # Force use of strongest model as requested
    model_to_use = MOST_POWERFUL_MODEL
    
    run_dir = None
    completed_ids = set()

    # Determine Run Directory
    if args.resume_from:
        run_dir = Path(args.resume_from)
        if not run_dir.exists():
            print(f"Error: Resume directory {run_dir} does not exist.")
            return
        print(f"Resuming run from: {run_dir}")
    elif args.resume_latest:
        runs_root = DATA_DIR / "benchmark_case_verification_runs"
        if runs_root.exists():
            subdirs = [d for d in runs_root.iterdir() if d.is_dir()]
            if subdirs:
                # Sort by name (timestamp) descending
                subdirs.sort(key=lambda x: x.name, reverse=True)
                run_dir = subdirs[0]
                print(f"Resuming latest run from: {run_dir}")
            else:
                print("No previous runs found to resume.")
                return
        else:
            print("No previous runs found to resume.")
            return

    if run_dir:
        # Scan for completed cases
        for report_path in run_dir.glob("**/report.json"):
            # Avoid the aggregated report
            if report_path.name == "report.json" and report_path.parent != run_dir:
                try:
                    with open(report_path, 'r') as f:
                        data = json.load(f)
                        if "id" in data:
                            completed_ids.add(data["id"])
                except Exception:
                    pass
        print(f"Found {len(completed_ids)} completed cases. These will be skipped.")
    else:
        # Create New Timestamped Run Directory
        import datetime as _dt
        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = DATA_DIR / "benchmark_case_verification_runs" / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"Starting verification run at: {run_dir}")
    
    api_key_manager = ApiKeyManager()
    
    files = []
    if args.target:
        target_path = Path(args.target)
        if target_path.is_file():
            files = [target_path]
        elif target_path.is_dir():
            files = list(target_path.glob("**/benchmark.yaml"))
    else:
        # Find all benchmark files first
        all_files = list(project_root.glob("benchmarks/benchmark_definitions/**/benchmark.yaml"))
        
        if args.suite_filter:
            # Filter based on suite name
            filters = [f.strip() for f in args.suite_filter.split(",") if f.strip()]
            for f in all_files:
                if any(flt in str(f) for flt in filters):
                    files.append(f)
        else:
            # Default to all multiple choice benchmarks (original behavior)
            files = [f for f in all_files if "_mc" in str(f.parent)]

    # Sort files for deterministic order
    files.sort()
    
    if not files:
        print("No benchmark files found.")
        return


    print(f"{Fore.CYAN}Found {len(files)} benchmark files to verify.{Style.RESET_ALL}")
    
    # Pre-count total test cases across all files
    total_cases = 0
    
    for f in files:
        
        import yaml
        with open(f, "r") as _yf:
            b = yaml.safe_load(_yf)

        if b:
            total_cases += len(b.get('benchmarks', []))
    
    print(f"{Fore.CYAN}Total benchmark cases to verify: {total_cases}{Style.RESET_ALL}\n")
    
    completed_cases = 0
    import time
    start_run_time = time.time()
    last_log_time = time.time()
    
    current_results = []
    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = []
    
    for f in files:
        tasks.append(verify_benchmark(
            f, run_dir, model_to_use, api_key_manager, skip_ids=completed_ids,
            repo_url=args.repo_url, repo_version=args.repo_version, setup_cmd=args.extra_dep,
            semaphore=semaphore,
            max_retries=args.max_retries,
            min_wait=args.min_wait,
            max_wait=args.max_wait
        ))
        
    all_file_results = await asyncio.gather(*tasks)
    
    for file_results in all_file_results:
        if file_results:
            current_results.extend(file_results)
            
    completed_cases = total_cases
    current_time = time.time()
    elapsed_minutes = (current_time - start_run_time) / 60
    import datetime as _dt
    timestamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.GREEN}[{timestamp}] - Verification Progress: {completed_cases}/{total_cases} tasks completed in {elapsed_minutes:.1f} minutes.{Style.RESET_ALL}\n")


    # --- Report Aggregation ---
    # Load existing results if any (from previous runs in the same dir)
    all_results = []
    report_json_path = run_dir / "aggregated_report.json"
    if report_json_path.exists():
        try:
            with open(report_json_path, 'r') as f:
                all_results = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load existing report: {e}")

    # Append new results (avoiding duplicates if re-running same case)
    existing_ids = {r['id'] for r in all_results}
    for res in current_results:
        if res['id'] not in existing_ids:
            all_results.append(res)
        else:
            # Update existing
            for i, r in enumerate(all_results):
                if r['id'] == res['id']:
                    all_results[i] = res
                    break
    
    # Save aggregated JSON
    with open(report_json_path, 'w') as f:
        json.dump(all_results, f, indent=2)

    # Generate Summary Report
    valid_count = sum(1 for r in all_results if r['verdict'] == 'Valid')
    ambiguous_count = sum(1 for r in all_results if r['verdict'] == 'Ambiguous')
    incorrect_count = sum(1 for r in all_results if r['verdict'] == 'Incorrect')
    error_count = sum(1 for r in all_results if r['verdict'] == 'Error')
    unknown_count = sum(1 for r in all_results if r['verdict'] == 'Unknown')
    
    summary_md = f"""# Benchmark Verification Report
**Date:** {timestamp}
**Target:** `{args.target}`
**Model:** `{args.model}`

## Summary
- **Total Cases:** {len(all_results)}
- **✅ Valid:** {valid_count}
- **⚠️ Ambiguous:** {ambiguous_count}
- **❌ Incorrect:** {incorrect_count}
- **🚨 Errors:** {error_count}
- **❓ Unknown:** {unknown_count}

## Detailed Findings
"""
    groups = {
        "Incorrect": [r for r in all_results if r['verdict'] == 'Incorrect'],
        "Ambiguous": [r for r in all_results if r['verdict'] == 'Ambiguous'],
        "Error": [r for r in all_results if r['verdict'] == 'Error'],
        "Unknown": [r for r in all_results if r['verdict'] == 'Unknown'],
        "Valid": [r for r in all_results if r['verdict'] == 'Valid'],
    }
    
    for group_name, parsed_results in groups.items():
        if not parsed_results:
            continue
            
        summary_md += f"\n## 🗂️ {group_name} Cases ({len(parsed_results)})\n\n"
        
        for r in parsed_results:
            verdict_icon = "✅" if r['verdict'] == "Valid" else "❌" if r['verdict'] == "Incorrect" else "⚠️"
            if r['verdict'] == "Error": verdict_icon = "🚨"
            
            slug = re.sub(r'[^a-zA-Z0-9_]', '_', r['id'])
            rel_path = f"./{slug}"
            
            summary_md += f"### `{r['id']}`\n"
            
            if r.get('question'):
                summary_md += f"**Question:** {r['question']}\n\n"
                
            summary_md += f"- **Verdict:** {verdict_icon} {r['verdict']}\n"
            summary_md += f"- **Tokens:** {r.get('tokens', 0):,}\n"
            
            prof = r.get('profiling', {})
            if prof:
                summary_md += f"- **Time Profile:** Total {prof.get('total_sec', 0)}s "
                summary_md += f"(Setup: {prof.get('setup_sec', 0)}s, LLM: {prof.get('agent_exec_sec', 0)}s, Format: {prof.get('format_sec', 0)}s)\n"
            
            # Add Claims
            eval_claims = r.get('details', {}).get('evaluated_claims')
            expected_ans = str(r.get('expected_answer')).strip()
            options_dict = r.get('options', {})
            
            if eval_claims:
                summary_md += "\n#### Evaluated Claims\n"
                for ec in eval_claims:
                    opt = str(ec.get('option')).strip()
                    ec_verdict = ec.get('verdict', 'Unknown')
                    ec_icon = "✅" if "Valid" in ec_verdict or "True" in ec_verdict or "Correct" in ec_verdict else "❌" if "Incorrect" in ec_verdict or "False" in ec_verdict else "⚠️" 
                    
                    status_text = "Valid Choice (Hypothesis Verified)" if "✅" in ec_icon else "Incorrect Choice (Verified Distractor)" if "❌" in ec_icon else ec_verdict
                    expected_badge = " **(🎯 Expected Correct Answer)**" if opt == expected_ans else ""
                    opt_text = options_dict.get(opt, "")
                    opt_display = f": `{opt_text}`" if opt_text else ""
                    
                    summary_md += f"- **Option {opt}**{expected_badge}{opt_display}\n  - *Evaluation:* {ec_icon} {status_text}\n  - *Details:* {ec.get('explanation')}\n"
            elif r.get('claims'):
                summary_md += "\n#### Claims Tested\n"
                for c in r['claims']:
                    opt = str(c.get('option')).strip()
                    expected_badge = " **(🎯 Expected Correct Answer)**" if opt == expected_ans else ""
                    summary_md += f"- **Option {opt}**{expected_badge}: {c.get('hypothesis')}\n"
            
            # Add details/fix
            if r.get('details', {}).get('suggested_fix'):
                summary_md += f"\n#### Suggested Fix\n{r['details']['suggested_fix']}\n"
                
            summary_md += f"\n👉 [View Full Case Artifacts and Logs]({rel_path})\n\n"
            summary_md += "---\n\n"

    summary_file = run_dir / "run_report.md"
    with open(summary_file, 'w') as f:
        f.write(summary_md)
    
    # Also save as JSON for programmatic use
    with open(run_dir / "aggregated_report.json", "w") as f:
        json.dump(all_results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
