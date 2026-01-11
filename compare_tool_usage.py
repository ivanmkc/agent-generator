

import json
import sys
from pathlib import Path

def estimate_tokens(text):
    if not text: return 0
    # Rough estimate: 4 chars per token
    return len(str(text)) // 4

def analyze_trace(file_path, label):
    print(f"\n--- Analyzing {label} ({file_path}) ---")
    if not Path(file_path).exists():
        print("File not found.")
        return

    events = []
    with open(file_path, 'r') as f:
        for line in f:
            try:
                item = json.loads(line)
                # Look for nested trace logs in test_result
                if item.get("event_type") == "test_result":
                    data = item.get("data", {})
                    # Check generation attempts (most detailed)
                    attempts = data.get("generation_attempts") or []
                    for attempt in attempts:
                        if attempt.get("trace_logs"):
                            events.extend(attempt["trace_logs"])
                    
                    # Fallback to top-level trace_logs if present
                    if not attempts and data.get("trace_logs"):
                        events.extend(data["trace_logs"])
                
            except: pass

    # Filter for tool interactions
    tool_sequence = []
    
    # Map tool_call_id to input for easy retrieval when result comes
    pending_tools = {}

    for e in events:
        # Standardize event keys (handle both top-level keys and potentially different schema)
        evt_type = e.get("type")
        
        if evt_type == "tool_use":
            tool_name = e.get("tool_name")
            # Handle parameters/tool_input variation
            tool_input = e.get("tool_input") or e.get("parameters")
            call_id = e.get("tool_call_id") or e.get("tool_id")
            
            if call_id:
                pending_tools[call_id] = {
                    "name": tool_name,
                    "input": tool_input
                }
            
        elif evt_type == "tool_result":
            call_id = e.get("tool_call_id") or e.get("tool_id")
            if call_id in pending_tools:
                call_info = pending_tools.pop(call_id)
                
                # Handle output/content variation
                raw_output = e.get("tool_output") or e.get("output") or e.get("content")
                
                # Sometimes output is a dict like {'result': '...'}
                if isinstance(raw_output, dict) and "result" in raw_output:
                    output = raw_output["result"]
                else:
                    output = str(raw_output)
                
                tool_sequence.append({
                    "step": len(tool_sequence) + 1,
                    "tool": call_info["name"],
                    "input": call_info["input"],
                    "output_len": len(output),
                    "est_tokens": estimate_tokens(output)
                })
        
        # Handle CLI structure if different (sometimes CLI stdout logs contain the full json)
        # The logs I saw earlier seemed to follow the tool_use/tool_result pattern.

    # Print Table
    print(f"{'#':<3} | {'Tool':<20} | {'Input Summary':<40} | {'Output Size':<10} | {'Est. Tokens'}")
    print("-" * 100)
    
    total_tool_tokens = 0
    
    for item in tool_sequence:
        inp_str = str(item['input'])
        if len(inp_str) > 38: inp_str = inp_str[:35] + "..."
        
        print(f"{item['step']:<3} | {item['tool']:<20} | {inp_str:<40} | {item['output_len']:<10} | {item['est_tokens']}")
        total_tool_tokens += item['est_tokens']
        
    print("-" * 100)
    print(f"Total Output Tokens (Tools Only): {total_tool_tokens}")

if __name__ == "__main__":
    # Path 1: Gemini CLI Run (from compare logs)
    analyze_trace("tmp/compare_logs/compare_trace.jsonl", "Gemini CLI + ADK")
    
    # Path 2: Optimized ADK Run (from optimize logs)
    analyze_trace("tmp/optimize_logs/optimize_trace.jsonl", "Optimized ADK Agent")
