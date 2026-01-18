from typing import List, Dict, Any
import re

class AttemptAnalysis:
    def __init__(self, attempt_data: Dict[str, Any]):
        self.trace_logs = attempt_data.get("trace_logs") or []
        self.error_message = attempt_data.get("error_message")
        self.status = attempt_data.get("status")
        self.ground_truth = attempt_data.get("ground_truth")
        self.answer = attempt_data.get("answer")
        
        # Computed Stats
        self.tools_used = []
        self.retrieval_steps = 0
        self.coding_attempts = 0
        self.has_sanitizer_hallucination = False
        self.loop_early_exit = False
        self.router_decision = None
        self.has_router = False
        self.final_code_present = False
        self.final_tool_output = None
        self.question = None
        
        self._audit_trace()

    def _audit_trace(self):
        for evt in self.trace_logs:
            author = evt.get("author", "unknown")
            content = str(evt.get("content", ""))
            tool_name = evt.get("tool_name")
            
            # Capture Question (First user message)
            if not self.question and evt.get("role") == "user" and content:
                # Basic cleaning: Remove "You are an expert..." boilerplate if likely
                clean_q = content
                if "Answer the following" in clean_q:
                    parts = clean_q.split("Answer the following")
                    if len(parts) > 1:
                        clean_q = parts[-1]
                
                # Truncate
                self.question = clean_q.strip()[:300] + "..." if len(clean_q) > 300 else clean_q.strip()

            # Router Check
            if author == "router":
                self.has_router = True
                if tool_name == "route_task":
                    inputs = evt.get("tool_input") or {}
                    self.router_decision = inputs.get("category", "UNKNOWN")

            # Sanitizer Hallucination Check
            if author == "prompt_sanitizer_agent" and "```json" in content:
                if '"code":' in content or "fully_qualified_class_name" in content:
                    self.has_sanitizer_hallucination = True

            # Tool Tracking
            if evt.get("type") == "tool_use":
                tool_args = evt.get("tool_input")
                self.tools_used.append({"name": tool_name, "args": tool_args, "output": None})
                
                if tool_name in ["list_ranked_targets", "search_ranked_targets", "inspect_fqn"]:
                    self.retrieval_steps += 1
                
                # Loop Early Exit Check
                if tool_name == "exit_loop" and author == "retrieval_worker":
                    self.loop_early_exit = True
            
            # Tool Output (Attach to last tool)
            if evt.get("type") == "tool_result" and self.tools_used:
                last_tool = self.tools_used[-1]
                # Verify matching call ID if possible, but sequential assumption usually holds in ADK
                output = evt.get("tool_output", "")
                last_tool["output"] = str(output)
                self.final_tool_output = str(output)[:500] # Capture last output

            # Code Gen
            if author == "candidate_creator" and "```python" in content:
                self.final_code_present = True
                self.coding_attempts += 1

def analyze_attempt(attempt_data: Dict[str, Any]) -> AttemptAnalysis:
    return AttemptAnalysis(attempt_data)
