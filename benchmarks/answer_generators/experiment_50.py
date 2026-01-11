"""
Experiment 50: Statistical Discovery V30 (Task-Based Delegation).
"""

from pathlib import Path
import tempfile
import os
import subprocess
import json
import re
import asyncio

from typing import AsyncGenerator

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent, LoopAgent
from google.adk.events import Event
from google.adk.tools import FunctionTool, ToolContext, exit_loop
from google.genai import types
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedRunner, CodeBasedFinalVerifier, CodeBasedTeardownAgent, RotatingKeyGemini, DocstringFetcherAgent
from benchmarks.answer_generators.debug_adk_agents import input_guard_callback
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.experiment_49 import _create_prismatic_retrieval_agents_v29

# --- Specialized Agents ---

def create_code_writer_tool(model, tools_helper) -> FunctionTool:
    """Creates a tool that runs the Code Writer Loop (V29 logic)."""
    
    # Re-create the V29 Solver components
    solver_agent = LlmAgent(
        name="code_solver",
        model=model,
        tools=[FunctionTool(tools_helper.read_file), FunctionTool(tools_helper.replace_text), FunctionTool(tools_helper.write_file)],
        include_contents='none',
        output_key="candidate_response",
        instruction=(
            """You are the Expert Codebase Solver.
Context: {knowledge_context}
Request: {sanitized_user_request}

Current State:
Previous Code: 
```python
{agent_code}
```
Feedback: 
{analysis_feedback}

**GOAL:** Write or fix the Python code to satisfy the request.
1. Use the Context to determine correct APIs.
2. If Feedback exists, fix the reported errors.
3. Output the code in a markdown block."""
        ),
    )

    code_runner = CodeBasedRunner(
        name="code_runner",
        tools_helper=tools_helper,
        model_name=model.model_name if hasattr(model, "model_name") else "gemini-2.5-flash"
    )

    analyst = LlmAgent(
        name="run_analyst",
        model=model,
        tools=[FunctionTool(exit_loop)],
        include_contents='none',
        output_key="analysis_feedback",
        instruction=(
            """Analyze the execution logs:
{run_output}

If SUCCESS: Call `exit_loop`.
If FAILURE: Explain the error to the solver."""
        )
    )

    loop_agent = LoopAgent(
        name="code_writing_loop",
        sub_agents=[solver_agent, code_runner, analyst],
        max_iterations=3
    )

    async def run_code_writer(tool_context: ToolContext) -> str:
        """
        Executes the specialized Code Writing Agent.
        Use this for tasks that involve writing, fixing, or implementing Python code/agents.
        """
        ctx = tool_context._invocation_context
        # Reset previous code to avoid stale state in new loop
        if "agent_code" not in ctx.session.state:
            ctx.session.state["agent_code"] = ""
            
        async for event in loop_agent.run_async(ctx):
             pass
        
        # The loop updates session state (agent_code), which is what we want.
        # We also grab the candidate response to pass back
        return ctx.session.state.get("candidate_response", "Error: No code generated.")

    return FunctionTool(run_code_writer)

def create_knowledge_tool(model) -> FunctionTool:
    """Creates a tool that runs the Knowledge/QA Agent."""
    
    qa_agent = LlmAgent(
        name="knowledge_expert",
        model=model,
        include_contents='none',
        output_key="candidate_response", # Writes to same key as solver for final output
        instruction=(
            """You are the ADK Knowledge Expert.
Context: {knowledge_context}
Question: {sanitized_user_request}

**GOAL:** Answer the question accurately based ONLY on the provided context.
- If it's a Multiple Choice Question, output JSON: `{"answer": "A", "rationale": "..."}`
- If it's an API Question, output JSON: `{"code": "ClassName", "fully_qualified_class_name": "..."}` or relevant format.
- Do NOT write implementation code unless asked for a snippet.
- Output RAW JSON only. No markdown blocks."""
        )
    )

    async def run_knowledge_expert(tool_context: ToolContext) -> str:
        """
        Executes the specialized Knowledge Expert Agent.
        Use this for Multiple Choice questions, API understanding questions, or general queries.
        """
        ctx = tool_context._invocation_context
        async for event in qa_agent.run_async(ctx):
            pass
        return ctx.session.state.get("candidate_response", "Error: No answer generated.")

    return FunctionTool(run_knowledge_expert)

class SmartFinalizerAgent(Agent):
    """
    Intelligently packages the result based on what's in the session state.
    Handles both Code Generation and QA outputs.
    """
    def __init__(self, tools_helper, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        candidate_str = ctx.session.state.get("candidate_response", "")
        agent_code = ctx.session.state.get("agent_code", "")
        user_req = ctx.session.state.get("sanitized_user_request", "")
        
        final_json = "{}"
        
        # Determine Task Type from Request
        task_type = "code"
        if "MultipleChoiceAnswerOutput" in user_req:
            task_type = "mc"
        elif "ApiUnderstandingAnswerOutput" in user_req:
            task_type = "api"
        
        # Helper to try parsing candidate as JSON
        candidate_data = {}
        try:
            clean_cand = candidate_str
            if "```json" in clean_cand:
                clean_cand = clean_cand.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_cand:
                clean_cand = clean_cand.split("```")[1].split("```")[0].strip()
            candidate_data = json.loads(clean_cand)
        except json.JSONDecodeError:
            pass

        if task_type == "mc":
            # Ensure we have 'answer' and 'rationale'
            ans = candidate_data.get("answer", "E") # Default to E (None) if failed
            rat = candidate_data.get("rationale", "Failed to generate rationale.")
            final_json = json.dumps({"answer": ans, "rationale": rat, "benchmark_type": "multiple_choice"})
            
        elif task_type == "api":
            # Ensure 'code' and 'fully_qualified_class_name'
            code = candidate_data.get("code", "Unknown")
            fqn = candidate_data.get("fully_qualified_class_name", "Unknown")
            rat = candidate_data.get("rationale", "Failed to generate rationale.")
            final_json = json.dumps({"code": code, "fully_qualified_class_name": fqn, "rationale": rat, "benchmark_type": "api_understanding"})
            
        else: # code
            # If agent_code is empty, try to extract from candidate_str
            if not agent_code:
                 match = re.search(r"```python\n(.*?)\n```", candidate_str, re.DOTALL)
                 if match:
                     agent_code = match.group(1)
                 else:
                     # Fallback: maybe the candidate IS the code?
                     agent_code = candidate_str

            # Write to file
            self._tools_helper.write_file("my_agent.py", agent_code)
            
            final_json = json.dumps({
                "code": agent_code,
                "rationale": "Implemented based on context.",
                "benchmark_type": "fix_error"
            })

        # 3. Save and Yield
        ctx.session.state["final_response"] = final_json
        yield Event(
            author=self.name,
            content=types.Content(role="model", parts=[types.Part(text=final_json)])
        )

def create_debug_structured_adk_agent_v30(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 50: V29 + Task Delegation + Smart Finalizer.
    """

    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name 

    setup_agent = SetupAgentCodeBased(
        name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper
    )

    prompt_sanitizer_agent = PromptSanitizerAgent(
        model=model,
        include_contents='none',
        output_key="sanitized_user_request",
    )

    retrieval_agents = _create_prismatic_retrieval_agents_v29(tools_helper, model)

    # --- Delegation Layer ---
    code_tool = create_code_writer_tool(model, tools_helper)
    qa_tool = create_knowledge_tool(model)
    
    delegator_agent = LlmAgent(
        name="delegator_agent",
        model=model,
        tools=[code_tool, qa_tool],
        include_contents='none',
        output_key="delegator_output",
        instruction=(
            """You are the Task Manager.
Request: {sanitized_user_request}

**DECISION:**
1. If the request asks to **fix code**, **implement an agent**, **write a script**, or **create a class**:
   -> Call `run_code_writer`.
   
2. If the request is a **Multiple Choice Question**, asks **"What is..."**, or asks about **API signatures**:
   -> Call `run_knowledge_expert`.

Call exactly ONE tool. The tool will execute the task and save the result."""
        )
    )

    final_verifier = SmartFinalizerAgent(
        name="final_verifier",
        tools_helper=tools_helper
    )

    teardown_agent = CodeBasedTeardownAgent(
        name="teardown_agent", 
        workspace_root=tools_helper.workspace_root, 
        tools_helper=tools_helper
    )

    agent_obj = SequentialAgent(
        name="delegation_solver_v30",
        sub_agents=[
            setup_agent,
            prompt_sanitizer_agent,
            *retrieval_agents,
            delegator_agent,
            final_verifier, 
            teardown_agent,
        ],
    )

    return agent_obj

def create_statistical_v30_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 50 (ADK_STATISTICAL_V30).
    """
    name_prefix="ADK_STATISTICAL_V30"
    folder_prefix="adk_stat_v30_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v30(tools_helper, model_name, api_key_manager)

    async def teardown_hook():
        pass

    return AdkAnswerGenerator(
        agent=agent, 
        name=f"{name_prefix}({model_name})", 
        setup_hook=setup_hook, 
        teardown_hook=teardown_hook, 
        api_key_manager=api_key_manager
    )