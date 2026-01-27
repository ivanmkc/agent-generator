# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for the Agentic Benchmark Generator agents."""

import ast
import os
import sys
import io
import time
import json
import random
import traceback
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict, Counter, deque

from google.adk.tools import ToolContext
from tools.benchmark_generator.models import TargetEntity, TargetType, GoldenSnapshot, DistractorOption, ValidationStatus, ContextNode
from tools.benchmark_generator.irt import IRTManager
from tools.benchmark_generator.logger import AgenticLogger
from tools.target_ranker.scanner import scan_repository

# --- Scanner (Cartographer) Logic ---

def list_prioritized_targets(tool_context: ToolContext, limit: int = 20) -> str:
    """
    Returns a prioritized list of target IDs using a stateful BFS strategy:
    1. High-Usage Seeds -> 2. Dependencies (BFS) -> 3. Orphans (Zero-usage, disconnected).
    The queue is computed once and cached in the session.
    """
    state = tool_context.session.state
    targets_data = state.get("scanned_targets", [])
    output_dir = state.get("output_dir")
    
    if not targets_data:
        # Fallback: Try loading from shared file
        if output_dir:
            shared_targets_path = Path(output_dir) / "scanned_targets.json"
            if shared_targets_path.exists():
                try:
                    with open(shared_targets_path, "r") as f:
                        targets_data = json.load(f)
                    state["scanned_targets"] = targets_data
                except Exception: pass

    if not targets_data: return "No targets scanned. Call scan_repository first."

    # Load processed list
    processed_list = state.get("processed_targets_list", [])
    if output_dir:
        processed_path = Path(output_dir) / "processed_targets.json"
        if processed_path.exists():
            try:
                with open(processed_path, "r") as f:
                    file_processed = json.load(f)
                processed_list = list(set(processed_list + file_processed))
                state["processed_targets_list"] = processed_list
            except Exception: pass
            
    processed_set = set(processed_list)

    # --- BFS Queue Generation (Cached) ---
    generation_queue = state.get("generation_queue")
    
    if not generation_queue:
        print("[DEBUG] Generating new BFS Target Queue...")
        # Map IDs to Entities for quick lookup
        entity_map = {t["id"]: t for t in targets_data}
        
        # 1. Build Graph
        cooccurrence_data = state.get("cooccurrence_data", {})
        associations = cooccurrence_data.get("associations", [])
        graph = defaultdict(list)
        for a in associations:
            # Context uses Target. Dependency: Context -> Target
            # We want to visit dependencies of used things.
            if a["context"] in entity_map and a["target"] in entity_map:
                graph[a["context"]].append(a["target"])

        # 2. Identify Seeds (Usage > 0)
        seeds = [t for t in targets_data if t.get("usage_score", 0) > 0]
        # Sort seeds by usage desc
        seeds.sort(key=lambda t: t.get("usage_score", 0), reverse=True)
        
        ordered_ids = []
        visited = set()
        
        # 3. Initialize & BFS
        # Add Seeds first
        for s in seeds:
            if s["id"] not in visited:
                visited.add(s["id"])
                ordered_ids.append(s["id"])
        
        # Expand (Queue behavior using index)
        idx = 0
        while idx < len(ordered_ids):
            curr_id = ordered_ids[idx]
            idx += 1
            
            # Add unvisited dependencies
            for dep_id in graph.get(curr_id, []):
                if dep_id not in visited:
                    visited.add(dep_id)
                    ordered_ids.append(dep_id)
                    
        # 4. Add Orphans (Unvisited Public Entities)
        orphans = [t for t in targets_data if t["id"] not in visited]
        # Sort orphans by name
        orphans.sort(key=lambda t: t.get("id"))
        
        for o in orphans:
            ordered_ids.append(o["id"])
            
        generation_queue = ordered_ids
        state["generation_queue"] = generation_queue
        print(f"[DEBUG] BFS Queue Generated. Total: {len(generation_queue)}. Seeds: {len(seeds)}. Visited in BFS: {len(visited)}. Orphans: {len(orphans)}.")

    # --- Selection ---
    # Filter out already processed targets
    candidates_ids = [tid for tid in generation_queue if tid not in processed_set]
    
    print(f"[DEBUG] Target Selection: Queue Size={len(generation_queue)}, Processed={len(processed_set)}, Remaining={len(candidates_ids)}")
    
    if not candidates_ids: return "DONE"
    
    # Return top N from the ordered list
    results = []
    entity_map = {t["id"]: t for t in targets_data}
    
    for tid in candidates_ids[:limit]:
        t = entity_map.get(tid)
        if t:
            results.append({
                "id": t["id"],
                "usage": t.get("usage_score", 0)
            })
            
    return json.dumps(results)

def select_target(target_id: str, tool_context: ToolContext) -> str:
    """
    Selects a specific target, performs context expansion, and prepares it for the Observer.
    Returns the full TargetEntity JSON for the Auditor to review.
    """
    # Clear previous turn artifacts to prevent leakage
    tool_context.session.state["current_snapshot"] = "None"
    tool_context.session.state["saboteur_output"] = "None"

    targets_data = tool_context.session.state.get("scanned_targets", [])
    target_dict = next((t for t in targets_data if t["id"] == target_id), None)
    
    if not target_dict:
        return f"Error: Target {target_id} not found."
    
    best = TargetEntity.model_validate(target_dict)
    
    # --- Context Expansion (BFS Chain) ---
    structure_map = tool_context.session.state.get("structure_map", {})
    alias_map = tool_context.session.state.get("alias_map", {})
    usage_stats = tool_context.session.state.get("usage_stats", {})
    cooccurrence_data = tool_context.session.state.get("cooccurrence_data", {})
    associations = cooccurrence_data.get("associations", [])
    
    def resolve_fqn(name):
        if name in structure_map: return name
        if name in alias_map: return resolve_fqn(alias_map[name])
        return name

    if associations:
        prob_map = defaultdict(dict)
        for a in associations:
            prob_map[a["context"]][a["target"]] = a["probability"]
        
        parts = best.id.split(".")
        start_node = None
        for i in range(len(parts), 0, -1):
            sub = ".".join(parts[:i])
            # Check if this node exists in our probability map or structure map
            if sub in prob_map or sub in structure_map:
                start_node = sub
                break
        
        # Fallback if ID is a method but structure map only has class/module keys
        if not start_node:
            start_node = best.id

        if start_node:
            queue = deque([(start_node, 1.0)])
            final_probs = {start_node: 1.0}
            threshold = 0.05
            
            # Robust Chain-Rule BFS (from adk_chain_prob.py)
            while queue:
                curr, p = queue.popleft()
                for neighbor, cond_p in prob_map.get(curr, {}).items():
                    new_p = p * cond_p
                    if new_p >= threshold and new_p > final_probs.get(neighbor, 0.0):
                        final_probs[neighbor] = new_p
                        queue.append((neighbor, new_p))
            
            context_nodes = []
            processed_context = set()
            
            def build_context_list(node_fqn, prob, parent=None):
                if node_fqn in processed_context: return
                processed_context.add(node_fqn)
                
                canonical = resolve_fqn(node_fqn)
                # If resolve_fqn failed or structure map is incomplete, try fuzzy matching
                if canonical not in structure_map:
                    # Try to find a match in structure map keys
                    last = node_fqn.split(".")[-1]
                    candidates = [k for k in structure_map.keys() if k.endswith(f".{last}") or k == last]
                    if candidates:
                        canonical = max(candidates, key=lambda x: len(os.path.commonprefix([x, node_fqn])))

                node_def = structure_map.get(canonical)
                context_nodes.append(ContextNode(id=canonical, type=node_def["type"] if node_def else "Unknown", probability=prob, usage=usage_stats.get(canonical, {}).get("total_calls", 0), parent_id=parent))
                
                # Recursively add children (like __init__) if it's a class
                if node_def and node_def["type"] == "Class":
                     for child_fqn in node_def.get("children", []):
                         child_def = structure_map.get(child_fqn)
                         if child_def and child_def["type"] == "Method" and child_def["name"] == "__init__":
                             build_context_list(child_fqn, 1.0, parent=canonical)

            for node_name, prob in sorted(final_probs.items(), key=lambda x: x[1], reverse=True):
                # Only include nodes that are NOT the start node itself (redundant)
                # unless we really want its definition in the context list too?
                # Usually best.source_code covers the target. Context covers dependencies.
                if node_name != start_node:
                    build_context_list(node_name, prob)
            
            best.associated_context = context_nodes

    # Populate source code
    if best.file_path:
        repo_path = tool_context.session.state.get("repo_path", ".")
        full_path = Path(repo_path) / best.file_path
        if full_path.exists():
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content)
                # Simple logic to find the node by name and type
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == best.name:
                        # For methods, check parent FQN if possible
                        node_fqn = best.id # Assume ID is FQN
                        # This is a bit naive but works for top-level classes and functions
                        best.source_code = ast.get_source_segment(content, node)
                        break
            except Exception: pass

    # Mark as processed
    processed_list = tool_context.session.state.get("processed_targets_list", [])
    processed_list.append(best.id)
    tool_context.session.state["processed_targets_list"] = processed_list
    
    # Persist to shared file
    output_dir = tool_context.session.state.get("output_dir")
    if output_dir:
        processed_path = Path(output_dir) / "processed_targets.json"
        try:
            with open(processed_path, "w") as f:
                json.dump(processed_list, f)
        except Exception: pass
    
    print(f"[DEBUG] select_target: Marked {best.id} as processed. Count is now {len(processed_list)}.")
    
    # --- Trace Logging ---
    if output_dir:
        logger = AgenticLogger(output_dir=Path(output_dir))
        # Recalculate queue stats for the log
        total_scanned = len(targets_data)
        remaining = total_scanned - len(processed_list)
        
        logger.log_trace("TARGET_SELECTED", {
            "target_id": best.id,
            "target_type": best.type,
            "queue_stats": {
                "total_scanned": total_scanned,
                "processed": len(processed_list),
                "remaining": remaining
            }
        })

    # Save to state for Auditor to "see"
    res_json = best.model_dump_json()
    tool_context.session.state["current_target_json"] = res_json
    return res_json



# --- Helper Functions ---

def check_syntax(code: str) -> Optional[str]:
    """Checks if the code has valid Python syntax. Returns error message or None."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"SyntaxError: {e}"

# --- Tracer Logic ---

def trace_execution(code: str, target_method: Any, tool_context: ToolContext) -> str:
    """Executes the provided code snippet to capture a Golden Snapshot."""
    target_name = "Unknown"
    if isinstance(target_method, dict):
        target_name = target_method.get('name', 'Unknown')
    elif isinstance(target_method, str):
        target_name = target_method
        
    print(f"[DEBUG] trace_execution CALLED for {target_name}")
    
    # Input Guard: Syntax Check
    syntax_error = check_syntax(code)
    if syntax_error:
        return json.dumps({"status": "error", "message": syntax_error})

    target = None
    try:
        if isinstance(target_method, dict):
            target = TargetEntity.model_validate(target_method)
        else:
            # Try to find target in state if only ID was provided
            targets_data = tool_context.session.state.get("scanned_targets", [])
            target_dict = next((t for t in targets_data if t["id"] == target_method or t["name"] == target_method), None)
            if target_dict:
                target = TargetEntity.model_validate(target_dict)
            else:
                 # Minimal TargetEntity if not found
                 target = TargetEntity(id=target_name, type=TargetType.METHOD, name=target_name, file_path="unknown")
    except Exception as e:
        return json.dumps({"error": f"Failed to initialize target entity: {e}"})

    stdout_capture = io.StringIO()
    original_stdout = sys.stdout
    start_time = time.time()
    
    repo_path = tool_context.session.state.get("repo_path")
    original_sys_path = sys.path[:]
    original_modules = sys.modules.copy() # Backup modules
    
    if repo_path:
        abs_repo_path = str(Path(repo_path).resolve())
        if abs_repo_path not in sys.path:
            sys.path.insert(0, abs_repo_path)

    try:
        sys.stdout = stdout_capture
        # Provide common imports and ADK types to the execution scope
        import typing
        from typing import Optional, List, Dict, Any, Union, Iterable, Tuple, Set, Type, Callable
        from google.adk.agents import LlmAgent, Agent, SequentialAgent, LoopAgent
        from google.adk.runners import Runner
        
        exec_scope = {
            "Optional": Optional,
            "List": List,
            "Dict": Dict,
            "Any": Any,
            "Union": Union,
            "Iterable": Iterable,
            "Tuple": Tuple,
            "Set": Set,
            "Type": Type,
            "Callable": Callable,
            "typing": typing,
            "json": json,
            "time": time,
            "os": os,
            "LlmAgent": LlmAgent,
            "Agent": Agent,
            "SequentialAgent": SequentialAgent,
            "LoopAgent": LoopAgent,
            "Runner": Runner,
        }
        
        # Use a fresh local scope for each execution
        local_scope: Dict[str, Any] = {}
        exec(code, exec_scope, local_scope)
        execution_time = time.time() - start_time
        stdout_content = stdout_capture.getvalue()
        
        captured_locals = {}
        for k, v in local_scope.items():
            if not k.startswith("__") and not callable(v) and not isinstance(v, type(sys)):
                try:
                    captured_locals[k] = repr(v)
                except:
                    captured_locals[k] = "<unrepresentable>"

        snapshot = GoldenSnapshot(
            target=target,
            valid_usage_code=code,
            stdout=stdout_content,
            return_value=captured_locals.get("result", "N/A"),
            local_vars=captured_locals,
            execution_time=execution_time
        )
        # Persistence Workaround: Save to File
        snapshot_file = Path("current_snapshot.json")
        with open(snapshot_file, "w", encoding="utf-8") as f:
            f.write(snapshot.model_dump_json())
            
        tool_context.session.state["current_snapshot"] = snapshot.model_dump()
        print(f"[DEBUG] Snapshot SAVED to {snapshot_file} and session state.")
        return json.dumps({"status": "success", "snapshot_summary": f"Executed in {execution_time:.2f}s"})
    except Exception as e:
        traceback_str = traceback.format_exc()
        return json.dumps({"status": "error", "message": str(e), "traceback": traceback_str})
    finally:
        sys.stdout = original_stdout
        sys.path = original_sys_path
        # STRICT restore of sys.modules to prevent pollution from exec()
        # This prevents mocks created inside exec() from leaking out.
        to_delete = [m for m in sys.modules if m not in original_modules]
        for m in to_delete:
            del sys.modules[m]
        sys.modules.update(original_modules)

# --- Sandbox Logic ---

def validate_mutant(mutant_code: str, tool_context: ToolContext) -> str:
    # Input Guard: Syntax Check
    syntax_error = check_syntax(mutant_code)
    if syntax_error:
        # Syntax errors are valid "crashes" for mutants, but we distinguish them
        return json.dumps({"valid": True, "reason": syntax_error, "status": ValidationStatus.FAIL_CRASH})

    snapshot_data = tool_context.session.state.get("current_snapshot")
    # Backup: Read from file
    if (not snapshot_data or snapshot_data == "None") and Path("current_snapshot.json").exists():
        try:
            with open("current_snapshot.json", "r", encoding="utf-8") as f:
                snapshot_data = json.load(f)
        except: pass

    if not snapshot_data or snapshot_data == "None":
        return json.dumps({"error": "No Golden Snapshot found in session state or file."})
    
    snapshot = GoldenSnapshot.model_validate(snapshot_data)
    stdout_capture = io.StringIO()
    original_stdout = sys.stdout
    
    repo_path = tool_context.session.state.get("repo_path")
    original_sys_path = sys.path[:]
    original_modules = sys.modules.copy()
    
    if repo_path:
        abs_repo_path = str(Path(repo_path).resolve())
        if abs_repo_path not in sys.path:
            sys.path.insert(0, abs_repo_path)

    try:
        sys.stdout = stdout_capture
        # Provide common imports and ADK types
        import typing
        from typing import Optional, List, Dict, Any, Union, Iterable, Tuple, Set, Type, Callable
        from google.adk.agents import LlmAgent, Agent, SequentialAgent, LoopAgent
        from google.adk.runners import Runner
        
        exec_scope = {
            "Optional": Optional,
            "List": List,
            "Dict": Dict,
            "Any": Any,
            "Union": Union,
            "Iterable": Iterable,
            "Tuple": Tuple,
            "Set": Set,
            "Type": Type,
            "Callable": Callable,
            "typing": typing,
            "json": json,
            "time": time,
            "os": os,
            "LlmAgent": LlmAgent,
            "Agent": Agent,
            "SequentialAgent": SequentialAgent,
            "LoopAgent": LoopAgent,
            "Runner": Runner,
        }
        
        local_scope: Dict[str, Any] = {}
        exec(mutant_code, exec_scope, local_scope)
        stdout_content = stdout_capture.getvalue()
        
        # Compare Results
        mutant_result = repr(local_scope.get("result", "N/A"))
        golden_result = str(snapshot.return_value)
        
        stdout_divergent = stdout_content.strip() != snapshot.stdout.strip()
        result_divergent = mutant_result != golden_result
        
        if not stdout_divergent and not result_divergent:
             print(f"[DEBUG] Mutant is EQUIVALENT. Stdout matched, Result ({mutant_result}) matched.")
             return json.dumps({"valid": False, "reason": "Equivalent Mutant"})
             
        reason = "Divergent Output"
        if stdout_divergent and result_divergent:
            reason = "Divergent Stdout and Return Value"
        elif stdout_divergent:
            reason = "Divergent Stdout"
        else:
            reason = "Divergent Return Value"

        return json.dumps({"valid": True, "reason": reason, "status": ValidationStatus.PASS})
    except Exception as e:
        return json.dumps({"valid": True, "reason": f"Runtime Crash: {e}", "status": ValidationStatus.PASS})
    finally:
        sys.stdout = original_stdout
        sys.path = original_sys_path
        to_delete = [m for m in sys.modules if m not in original_modules]
        for m in to_delete:
            del sys.modules[m]
        sys.modules.update(original_modules)

# --- Assembly Logic ---

def assemble_and_save_benchmark(explanation: str, tool_context: ToolContext) -> str:
    """
    Programmatically assembles the benchmark case from session state and saves it.
    This eliminates the need for the LLM to copy-paste code blocks.
    """
    snapshot_data = tool_context.session.state.get("current_snapshot")
    # Backup: Read from file
    if (not snapshot_data or snapshot_data == "None") and Path("current_snapshot.json").exists():
        try:
            with open("current_snapshot.json", "r", encoding="utf-8") as f:
                snapshot_data = json.load(f)
        except: pass

    saboteur_output = tool_context.session.state.get("saboteur_output")
    target_data = tool_context.session.state.get("current_target_json")

    if not snapshot_data or snapshot_data == "None":
        return json.dumps({"error": "Missing Golden Snapshot. Observer might have failed or trace_execution wasn't called."})
    
    # Parse Saboteur Output safely
    mutants = []
    try:
        if isinstance(saboteur_output, str):
            # Try to find JSON block if it's wrapped in markdown
            raw_str = saboteur_output.strip()
            if "```json" in raw_str:
                raw_str = raw_str.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_str:
                raw_str = raw_str.split("```")[1].split("```")[0].strip()
            
            if not raw_str:
                 return json.dumps({"error": f"Saboteur output string is empty after stripping markdown. Raw: {saboteur_output[:100]}..."})

            parsed = json.loads(raw_str)
            mutants = parsed.get("mutants") or parsed.get("distractors") or []
        elif isinstance(saboteur_output, dict):
            mutants = saboteur_output.get("mutants") or saboteur_output.get("distractors") or []
        else:
            return json.dumps({"error": f"Unexpected saboteur_output type: {type(saboteur_output)}. Expected str or dict."})
    except Exception as e:
        return json.dumps({"error": f"Failed to parse mutants from saboteur_output: {e}. Raw content: {str(saboteur_output)[:200]}..."})

    if not isinstance(mutants, list) or len(mutants) < 3:
        return json.dumps({"error": f"Insufficient mutants found: {len(mutants) if isinstance(mutants, list) else 'Not a list'}. Need 3."})

    # Prepare Data
    try:
        if isinstance(snapshot_data, str):
            if not snapshot_data or snapshot_data == "None":
                return json.dumps({"error": "Missing Golden Snapshot. Observer might have failed or trace_execution wasn't called."})
            snapshot_data = json.loads(snapshot_data)
        
        if isinstance(target_data, str):
            if not target_data or target_data == "None":
                return json.dumps({"error": "Missing Target Data. Auditor might have failed to select a target."})
            target_data = json.loads(target_data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Failed to parse JSON from state: {e}. target_data type: {type(target_data)}"})
    
    golden_code = snapshot_data.get("valid_usage_code")
    target_name = target_data.get("name", "Target")

    # --- Randomization Logic ---
    candidates = [
        {"code": golden_code, "type": "correct"},
        {"code": mutants[0]["code"], "type": "distractor"},
        {"code": mutants[1]["code"], "type": "distractor"},
        {"code": mutants[2]["code"], "type": "distractor"}
    ]

    # 20% chance to replace the last distractor with "None of the above"
    if random.random() < 0.2:
        candidates[3] = {"code": "None of the above", "type": "distractor"}

    random.shuffle(candidates)

    options = {}
    correct_letter = "A"
    
    letters = ["A", "B", "C", "D"]
    for i, cand in enumerate(candidates):
        letter = letters[i]
        options[letter] = cand["code"]
        if cand["type"] == "correct":
            correct_letter = letter

    # Construct Question
    question = f"Which of the following code snippets correctly initializes/uses `{target_name}`?"

    # Assemble Case
    case = {
        "question": question,
        "options": options,
        "correct_answer": correct_letter,
        "explanation": explanation,
        "benchmark_type": "multiple_choice"
    }
    
    # Save using the existing logic
    return save_benchmark_case(
        tool_context=tool_context,
        question=question,
        options=options,
        correct_answer=correct_letter,
        explanation=explanation
    )

# --- Dedup Logic ---

def check_uniqueness(question_text: str, tool_context: ToolContext) -> str:
    existing_benchmarks = tool_context.session.state.get("generated_benchmarks", [])
    if not existing_benchmarks:
        return json.dumps({"unique": True, "score": 1.0})
    def jaccard_sim(str1, str2):
        a, b = set(str1.split()), set(str2.split())
        return float(len(a.intersection(b))) / (len(a.union(b)))
    max_sim = max(jaccard_sim(question_text, b.get("question", "")) for b in existing_benchmarks)
    return json.dumps({"unique": max_sim < 0.8, "max_similarity": max_sim})

def save_benchmark_case(tool_context: ToolContext, question: Optional[str] = None, options: Optional[Dict[str, str]] = None, correct_answer: Optional[str] = None, explanation: Optional[str] = None, case_json: Optional[str] = None) -> str:
    """
    Saves a benchmark case to the session state and persistent logs.
    Can be called with individual fields or a JSON string.
    """
    try:
        case = {}
        if case_json:
            if isinstance(case_json, str):
                case = json.loads(case_json)
            elif isinstance(case_json, dict):
                case = case_json
        else:
            case = {
                "question": question,
                "options": options,
                "correct_answer": correct_answer,
                "explanation": explanation
            }
        
        # Schema Normalization
        normalized_case = {}
        
        # 1. Question
        q_val = case.get("question") or case.get("q")
        if not q_val:
             return json.dumps({"error": f"Missing 'question' field. Received keys: {list(case.keys())}"})
        normalized_case["question"] = q_val

        # 2. Options
        opts = case.get("options")
        if not opts or not isinstance(opts, dict):
            # Try fallback to A/B/C/D keys
            opts = {}
            for k in ["A", "B", "C", "D", "a", "b", "c", "d"]:
                if k in case: opts[k.upper()] = str(case[k])
        
        if not opts:
             return json.dumps({"error": "Missing or invalid options."})
        normalized_case["options"] = opts

        # 3. Correct Answer Extraction
        mapping = {0: "A", 1: "B", 2: "C", 3: "D", "0": "A", "1": "B", "2": "C", "3": "D"}
        raw_ans_key = case.get("correct_answer")
        if raw_ans_key is None:
            idx = case.get("correct_idx")
            if idx in mapping: raw_ans_key = mapping[idx]
        
        raw_ans_key = str(raw_ans_key) if raw_ans_key else "A"
        
        # --- ENFORCED RANDOMIZATION ---
        # To eliminate LLM positional bias (e.g. always putting correct answer in A),
        # we reshuffle the options here and re-map the correct answer key.
        
        # 1. Identify the Correct Answer Text
        correct_text = opts.get(raw_ans_key)
        if not correct_text:
             # Fallback: If key not found, assume the first option was intended or log warning
             # For robustness, we'll just skip shuffling if we can't identify the truth.
             print(f"[WARN] Could not find text for correct_answer key '{raw_ans_key}'. Skipping shuffle.")
             normalized_case["options"] = opts
             normalized_case["correct_answer"] = raw_ans_key
        else:
            # 2. Collect and Shuffle
            option_texts = list(opts.values())
            random.shuffle(option_texts)
            
            # 3. Re-assign Keys
            new_options = {}
            new_correct_key = None
            keys = ["A", "B", "C", "D"]
            
            for i, text in enumerate(option_texts):
                # Handle cases with > 4 options if necessary, though benchmarks usually have 4
                key = keys[i] if i < 4 else chr(ord('A') + i)
                new_options[key] = text
                if text == correct_text:
                    new_correct_key = key
            
            normalized_case["options"] = new_options
            normalized_case["correct_answer"] = new_correct_key

        # 4. Explanation
        normalized_case["explanation"] = case.get("explanation") or case.get("context") or "No explanation provided."
        normalized_case["benchmark_type"] = "multiple_choice"

        # Update Session State
        state = tool_context.session.state
        current_list = state.get("generated_benchmarks", [])
        if not isinstance(current_list, list):
            print(f"[DEBUG] Fix state: generated_benchmarks was {type(current_list)}, resetting to list.")
            current_list = []
        
        # Inject ID
        normalized_case["id"] = f"agentic_{int(time.time())}_{len(current_list)}"
        
        # --- Persistence ---
        output_dir = state.get("output_dir")
        raw_log_path = Path(output_dir) / "raw_benchmarks.jsonl" if output_dir else Path("tmp/outputs/agentic_generated_raw.jsonl")
        yaml_path = Path(output_dir) / "benchmark_partial.yaml" if output_dir else None
        
        # 1. YAML (Strict)
        if yaml_path:
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            first_write = not yaml_path.exists() or yaml_path.stat().st_size == 0
            yaml_case = {
                "question": normalized_case["question"],
                "options": normalized_case["options"],
                "correct_answer": normalized_case["correct_answer"],
                "explanation": normalized_case["explanation"],
                "benchmark_type": "multiple_choice"
            }
            with open(yaml_path, "a", encoding="utf-8") as f:
                if first_write: f.write("benchmarks:\n")
                f.write(yaml.safe_dump([yaml_case], sort_keys=False))

        # 2. JSONL
        raw_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(raw_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(normalized_case) + "\n")

        # 3. State Update
        state["generated_benchmarks"] = current_list + [normalized_case]
        
        # 4. Trace Log
        if output_dir:
            total = len(state.get("scanned_targets", []))
            processed = len(state.get("processed_targets_list", []))
            coverage_pct = (processed / total * 100) if total > 0 else 0.0
            
            logger = AgenticLogger(output_dir=Path(output_dir))
            logger.log_trace("BENCHMARK_SAVED", {
                "benchmark_id": normalized_case["id"],
                "target_id": state.get("current_target_json", "{}"), # Best effort
                "stats": {"coverage_pct": coverage_pct, "processed_count": processed}
            })
            
        return f"SUCCESS: Benchmark saved. Total now: {len(current_list) + 1}."
    except Exception as e:
        traceback.print_exc()
        return f"ERROR: Failed to save case: {str(e)}"