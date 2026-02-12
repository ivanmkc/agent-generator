            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML {benchmark_file}: {e}")
        return
        
    benchmarks = data.get('benchmarks', [])
    if not benchmarks:
        print("No benchmarks found in file.")
        return

    results = []
    
    # Extract sandbox config if it exists at root level of benchmark.yaml
    yaml_target_repo = data.get("target_repo_url", repo_url)
    yaml_target_version = data.get("target_repo_version", repo_version)
    yaml_extra_deps = data.get("extra_dependencies", setup_cmd)

    # Initialize the verifier generator
    generator = create_verifier_adk_generator(
        model_name=model_name, 
        api_key_manager=api_key_manager,
        benchmark_type=data.get("benchmarks", [{}])[0].get("benchmark_type", "multiple_choice"),
        target_repo_url=yaml_target_repo,
        target_repo_version=yaml_target_version,
        extra_dependencies=yaml_extra_deps
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
            
            print(f"\n  {Style.BRIGHT}{Fore.BLUE}▶ Verifying Case: {case_id}{Style.RESET_ALL}")
            print(f"    {Fore.LIGHTBLACK_EX}Artifacts: {case_output_dir}{Style.RESET_ALL}")
            
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
                response, trace_logs, usage_metadata, _ = await asyncio.wait_for(generator._run_agent_async(prompt, benchmark_type="verification"), timeout=600)
                
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
                    dirs_to_check = [workspace_dir]
                    
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
                        print(f"    {Fore.GREEN}✔ Archived {found_files} files to {artifacts_dir}{Style.RESET_ALL}")
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

                
                v_color = Fore.GREEN if verdict == "Valid" else Fore.RED if verdict == "Incorrect" else Fore.YELLOW if verdict == "Ambiguous" else Fore.WHITE
                v_icon = "✅" if verdict == "Valid" else "❌" if verdict == "Incorrect" else "⚠️" if verdict == "Ambiguous" else "❓"
                print(f"    {Style.BRIGHT}{v_color}{v_icon} Verdict: {verdict}{Style.RESET_ALL}")
                
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
                    "artifact_path": str(case_output_dir)
                }
                
                results.append(case_result)
                
                # Save individual case report
                with open(case_output_dir / "report.json", "w") as f:
                    json.dump(case_result, f, indent=2)

            except TimeoutError as e:
                print(f"    Timeout verifying case {case_id}: 10 minute limit exceeded.")
                results.append({
                    "id": case_id,
                    "verdict": "Error",
                    "error": "Timeout (10 minutes) exceeded.",
                    "question": case.get("question"),
                    "options": case.get("options", {}),
                    "expected_answer": case.get("correct_answer")
                })
            except Exception as e:
                print(f"    Error verifying case {case_id}: {e}")
                traceback.print_exc()
                results.append({
                    "id": case_id,
                    "verdict": "Error",
                    "error": str(e),
                    "question": case.get("question"),
                    "options": case.get("options", {}),
                    "expected_answer": case.get("correct_answer")
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
    
    # Generic Repository Sandboxing Settings
    parser.add_argument("--repo-url", help="Target repository URL for the code context", default="https://github.com/google/adk-python.git")
    parser.add_argument("--repo-version", help="Version/Branch of the target repository", default="v1.20.0")
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
        runs_root = VERIFICATION_RUNS_DIR
        if runs_root.exists():
            subdirs = [d for d in runs_root.iterdir() if d.is_dir()]
