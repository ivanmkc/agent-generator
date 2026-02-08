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

from benchmarks.answer_generators.verifier_agents import create_verifier_adk_generator
from core.api_key_manager import ApiKeyManager, KeyType
from benchmarks.answer_generators.adk_context import adk_execution_context
from core.config import DATA_DIR, PROJECT_ROOT, MOST_POWERFUL_MODEL, OUTPUT_ROOT
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
import datetime

# ... imports ...

async def verify_benchmark(
    benchmark_file: Path,
    run_dir: Path,
    model_name: str,
    api_key_manager: ApiKeyManager,
    skip_ids: Optional[set] = None
):
    """Verifies a single benchmark file."""
    if skip_ids is None:
        skip_ids = set()

    try:
        rel_path = benchmark_file.relative_to(PROJECT_ROOT)
    except ValueError:
        rel_path = benchmark_file
        
    print(f"\n=== Verifying {rel_path} ===")
    
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

    results = []
    
    # Initialize the verifier generator
    generator = create_verifier_adk_generator(
        model_name=model_name, 
        api_key_manager=api_key_manager,
        adk_branch="v1.20.0" 
    )
    
    token = None
    try:
        await generator.setup()
        
        if api_key_manager:
            current_key, api_key_id = await api_key_manager.get_key_for_run(f"verifier_{benchmark_file.stem}", KeyType.GEMINI_API)
            token = adk_execution_context.set({"api_key": current_key, "key_id": api_key_id})
        
        for case in benchmarks:
            case_id = case.get('id')
            
            if case_id in skip_ids:
                print(f"  > Skipping Case (Already Verified): {case_id}")
                continue

            # Create persistent case folder
            slug = re.sub(r'[^a-zA-Z0-9_]', '_', case_id)
            case_output_dir = run_dir / slug
            case_output_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"  > Verifying Case: {case_id}")
            print(f"    Artifacts: {case_output_dir}")
            
            # Construct the prompt for the Verifier Agent
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
            
            try:
                # Use internal method to run with raw prompt
                response, trace_logs, usage_metadata, _ = await generator._run_agent_async(prompt, benchmark_type="verification")
                
                # Print detailed logs
                print_verification_details(trace_logs)
                
                # Print Usage Statistics
                print(f"{Style.BRIGHT}{Fore.MAGENTA}=== Usage Statistics ==={Style.RESET_ALL}")
                if usage_metadata:
                    print(f"Total Tokens: {usage_metadata.total_tokens}")
                    print(f"Prompt Tokens: {usage_metadata.prompt_tokens}")
                    print(f"Completion Tokens: {usage_metadata.completion_tokens}")
                    if usage_metadata.extra_tags:
                        print(f"Latency/Stats: {json.dumps(usage_metadata.extra_tags, indent=2)}")
                print(f"{Style.BRIGHT}{Fore.MAGENTA}========================{Style.RESET_ALL}\n")
                
                # --- Artifact Archival ---
                workspace_dir = None
                claims = []
                
                # Extract workspace dir and claims from logs
                for event in trace_logs:
                    author = getattr(event, 'author', '')
                    content = getattr(event, 'content', '')
                    if not content: continue
                    
                    # 1. Look for workspace_dir in setup_agent output
                    if author == 'setup_agent' and '"workspace_dir"' in str(content):
                        try:
                            # Try parsing as JSON first
                            if isinstance(content, str):
                                # Clean up potential "For context: [setup_agent] said: " prefix if present in concatenated text
                                clean_content = content
                                if "said: " in content:
                                    clean_content = content.split("said: ", 1)[1]
                                data = json.loads(clean_content)
                            else:
                                data = content
                            if isinstance(data, dict) and "workspace_dir" in data:
                                workspace_dir = Path(data["workspace_dir"])
                        except:
                            # Fallback to regex
                            match = re.search(r'"workspace_dir":\s*"([^"]+)"', str(content))
                            if match:
                                workspace_dir = Path(match.group(1).replace('\\\\', '\\'))

                    # 2. Look for claims in claim_analyst output
                    if author == 'claim_analyst' and '"option"' in str(content):
                        try:
                            match = re.search(r"```json\s*([\s\S]*?)\s*```", str(content), re.IGNORECASE)
                            if match:
                                claims = json.loads(match.group(1))
                        except:
                            pass
                
                if workspace_dir and workspace_dir.exists():
                    artifacts_dir = case_output_dir / "workspace_files"
                    artifacts_dir.mkdir(exist_ok=True)
                    # Copy generated files (scripts, tests)
                    found_files = 0
                    
                    # The files might be in the task subdir or the root workspace depending on agent behavior.
                    # AdkTools defaults to root. SetupAgent creates a subdir.
                    # We check both.
                    dirs_to_check = [workspace_dir, workspace_dir.parent]
                    
                    for source_dir in dirs_to_check:
                        if not source_dir.exists(): continue
                        for file_path in source_dir.glob("*"):
                            if file_path.is_file() and file_path.suffix in ['.py', '.txt', '.md', '.json', '.log']:
                                # Avoid copying from venv or hidden files if they ended up here
                                if "venv" in str(file_path): continue
                                
                                try:
                                    shutil.copy2(file_path, artifacts_dir)
                                    found_files += 1
                                except Exception:
                                    pass
                        if found_files > 0:
                            # If we found files in the task dir, great. If not, we checked parent.
                            # Usually we don't want to copy the ENTIRE root if it's shared, but here
                            # the root is per-generator (and we assume sequential usage or one-off).
                            pass

                    if found_files > 0:
                        print(f"    Archived {found_files} files to {artifacts_dir}")
                else:
                    print(f"    Warning: Could not locate workspace artifacts at {workspace_dir}")
                
                # Save Trace Logs
                with open(case_output_dir / "trace_logs.json", "w") as f:
                    json.dump([e.model_dump(mode='json') for e in trace_logs], f, indent=2)

                # Extract verdict from response
                verdict = "Unknown"
                details = {}
                
                # Try to parse JSON block from response (flexible regex)
                match = re.search(r"```json\s*([\s\S]*?)\s*```", response, re.IGNORECASE)
                if match:
                    try:
                        details = json.loads(match.group(1))
                        verdict = details.get("verdict", "Unknown")
                    except:
                        pass
                
                # Fallback to text parsing if JSON fails or verdict still Unknown
                if verdict == "Unknown":
                    if re.search(r"Verdict:\s*Valid", response, re.IGNORECASE):
                        verdict = "Valid"
                    elif re.search(r"Verdict:\s*Ambiguous", response, re.IGNORECASE):
                        verdict = "Ambiguous"
                    elif re.search(r"Verdict:\s*Incorrect", response, re.IGNORECASE):
                        verdict = "Incorrect"

                print(f"    Verdict: {verdict}")
                
                case_result = {
                    "id": case_id,
                    "verdict": verdict,
                    "details": details,
                    "claims": claims,
                    "full_response": response,
                    "tokens": usage_metadata.total_tokens if usage_metadata else 0,
                    "artifact_path": str(case_output_dir)
                }
                
                results.append(case_result)
                
                # Save individual case report
                with open(case_output_dir / "report.json", "w") as f:
                    json.dump(case_result, f, indent=2)

            except Exception as e:
                print(f"    Error verifying case {case_id}: {e}")
                traceback.print_exc()
                results.append({
                    "id": case_id,
                    "verdict": "Error",
                    "error": str(e)
                })

    except Exception as e:
        print(f"Generator Setup/Run failed: {e}")
        traceback.print_exc()
    finally:
        if token:
            adk_execution_context.reset(token)
        await generator.teardown()
    
    return results

async def main():
    parser = argparse.ArgumentParser(description="Verify benchmark quality.")
    parser.add_argument("--model", default=MOST_POWERFUL_MODEL, help="Model to use (ignored, using strongest model).")
    parser.add_argument("--target", help="Specific benchmark file or directory.")
    parser.add_argument("--suite-filter", help="Substring filter for benchmark suites (e.g., 'mc', 'fix_errors').")
    parser.add_argument("--resume-from", help="Resume from a specific run directory.")
    parser.add_argument("--resume-latest", action="store_true", help="Resume from the most recent run directory.")
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
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
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

    print(f"Found {len(files)} benchmark files to verify.")
    
    current_results = []
    for f in files:
        file_results = await verify_benchmark(f, run_dir, model_to_use, api_key_manager)
        if file_results:
            current_results.extend(file_results)

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
    for r in all_results:
        verdict_icon = "✅" if r['verdict'] == "Valid" else "❌" if r['verdict'] == "Incorrect" else "⚠️"
        if r['verdict'] == "Error": verdict_icon = "🚨"
        
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', r['id'])
        rel_path = f"./{slug}"
        
        summary_md += f"### `{r['id']}`\n"
        summary_md += f"- **Verdict:** {verdict_icon} {r['verdict']}\n"
        summary_md += f"- **Tokens:** {r.get('tokens', 0):,}\n"
        
        # Add Claims
        if r.get('claims'):
            summary_md += "\n#### Claims Tested\n"
            for c in r['claims']:
                summary_md += f"- **Option {c.get('option')}:** {c.get('hypothesis')}\n"
        
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
