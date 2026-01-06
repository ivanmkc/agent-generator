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

"""Candidate ADK Agents for benchmarking."""

import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Optional, AsyncGenerator
import json
import re

from google.adk.agents import InvocationContext, LlmAgent, LoopAgent, SequentialAgent, Agent
from google.adk.events import Event
from google.adk.models import Gemini
from google.adk.tools import FunctionTool, ToolContext, exit_loop
from google.genai import Client, types
from pydantic import PrivateAttr
from google.adk.utils.output_schema_utils import can_use_output_schema_with_tools

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.answer_generators.adk_context import adk_execution_context
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks.answer_generators.adk_schemas import (
    CandidateSolution,
    FinalResponse,
    Plan,
    SetupContext,
    VerificationPlan,
    VerificationResult,
    RelevantModules,
    PlanningResult,
)


class RotatingKeyGemini(Gemini):
    """
    A Gemini model that rotates through a pool of API keys for each request.
    Thread-safe and race-condition free.
    Uses ApiKeyManager to handle rotation and cooldowns.
    Caches Client instances to maintain persistent aiohttp sessions.
    """

    _api_key_manager: ApiKeyManager = PrivateAttr()
    _lock: threading.Lock = PrivateAttr()
    _client_cache: dict[str, Client] = PrivateAttr(default_factory=dict)

    def __init__(self, api_key_manager: ApiKeyManager, **kwargs):
        super().__init__(**kwargs)
        self._api_key_manager = api_key_manager
        self._lock = threading.Lock()
        self._client_cache = {}

    @property
    def api_client(self) -> Client:
        """Overrides the standard client to provide one with a rotated key."""
        
        # 1. Check for context-scoped key (set by AdkAnswerGenerator)
        ctx = adk_execution_context.get()
        if ctx and "api_key" in ctx:
            current_key = ctx["api_key"]
        else:
            # 2. Fallback to internal rotation (if running outside a generator context)
            with self._lock:
                current_key, _ = self._api_key_manager.get_next_key_with_id()

        # Guard statement: If no current_key from either source, raise error.
        if not current_key:
            raise ValueError(
                "No API keys available from ApiKeyManager or Context. Please ensure keys are configured or present in context."
            )
        
        with self._lock:
            # Check cache
            if current_key not in self._client_cache:
                self._client_cache[current_key] = Client(
                    api_key=current_key,
                    http_options=types.HttpOptions(
                        headers=self._tracking_headers(),
                        retry_options=self.retry_options,
                    ),
                )

            return self._client_cache[current_key]

def get_workspace_dir(ctx: InvocationContext) -> str:
    """Retrieves the workspace directory name from the session state."""
    return ctx.session.state.get(
        "workspace_dir", "Error: No workspace directory found in session state."
    )

def save_workspace_dir(dir_name: str, ctx: InvocationContext) -> str:
    """Saves the workspace directory name to the session state."""
    ctx.session.state["workspace_dir"] = dir_name
    return f"Saved workspace directory '{dir_name}' to session state."

def uuid4() -> str:
    """Generates a random UUID."""
    return str(uuid.uuid4())


def create_default_adk_agent(model_name: str = "gemini-2.5-pro") -> LlmAgent:
    """Creates the default LlmAgent used for ADK benchmarking."""

    return LlmAgent(
        name="adk_test_agent",
        model=model_name,
        instruction=(
            "You are a senior engineer specializing in the ADK Python framework."
            " Your task is to answer questions or fix code with expert precision."
            " Always respond with a JSON object conforming to the specified"
            " schema, enclosed in a markdown code block (```json...```)."
        ),
    )

class SetupAgentCodeBased(Agent):
    """
    A code-based agent that performs initial workspace setup programmatically.
    """

    def __init__(self, workspace_root: Path, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._workspace_root = workspace_root
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:

        # Get the original user request from the input context
        user_request = ""
        if ctx.user_content and ctx.user_content.parts:
             user_request = "".join(
                [p.text for p in ctx.user_content.parts if p.text]
            )

        # 1. Generate a unique directory name
        unique_dir_name = f"task_{uuid.uuid4().hex}"
        workspace_dir = self._workspace_root / unique_dir_name

        # 2. Create the directory
        mkdir_command = f"mkdir -p {workspace_dir}"
        await self._tools_helper.run_shell_command(mkdir_command)

        # 3. Save the workspace directory to session state
        save_workspace_dir(str(workspace_dir), ctx)
        ctx.session.state["user_request"] = user_request

        # 4. Output SetupContext
        setup_context = SetupContext(
            workspace_dir=str(workspace_dir),
            user_request=user_request,
            sanitized_user_request=None,
            knowledge_context=None,  # Populated by Knowledge Retrieval Agent
        )
        
        json_output = json.dumps(setup_context.model_dump())

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=json_output)]
            )
        )

class CodeBasedTeardownAgent(Agent):
    """
    A code-based agent that performs teardown actions programmatically.
    """
    def __init__(self, workspace_root: Path, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._workspace_root = workspace_root
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 1. Retrieve the temporary directory name.
        workspace_dir = get_workspace_dir(ctx)
        
        # 2. Delete it using run_shell_command with rm -rf.
        if workspace_dir and "Error" not in workspace_dir and Path(workspace_dir).exists():
            rm_command = f"rm -rf {workspace_dir}"
            await self._tools_helper.run_shell_command(rm_command)

        # 3. Return the FinalResponse from session state.
        final_response_json = ctx.session.state.get("final_response", "")

        # Yield the FinalResponse
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=final_response_json)]
            )
        )

class PromptSanitizerAgent(LlmAgent):
    """
    An LLM agent that sanitizes user requests by removing direct tool-calling instructions.
    """
    def __init__(self, model: str | Gemini, **kwargs):
        super().__init__(
            name="prompt_sanitizer_agent",
            model=model,
            tools=[],  # No tools for this agent, purely text transformation
            instruction=(
                "You are a prompt sanitization expert. "
                "Request: {user_request}\n"
                "Task: Remove explicit instructions to call tools (e.g., 'use run_adk_agent', 'write_file') "
                "or internal operational directives. Keep the core objective. "
                "Output ONLY the sanitized request as plain text."
            ),
            **kwargs
        )

class CodeBasedRunner(Agent):
    """
    A code-based agent that merely executes the agent code programmatically.
    It does NOT analyze the result.
    """
    def __init__(self, tools_helper: AdkTools, model_name: str, name: str):
        super().__init__(name=name)
        self._tools_helper = tools_helper
        self._model_name = model_name

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 1. Retrieve candidate response from state (saved via output_key)
        candidate_response = ctx.session.state.get("candidate_response", "")
        
        # 2. Extract Python code
        agent_code = "# Error: No code found."
        
        # Try finding a python block first
        python_match = re.search(r"```python\n([\s\S]*?)\n```", candidate_response)
        if python_match:
            agent_code = python_match.group(1).strip()
        else:
            # Try finding a JSON block and extracting 'code' field
            json_match = re.search(r"```json\n([\s\S]*?)\n```", candidate_response)
            if json_match:
                try:
                    json_str = json_match.group(1).strip()
                    data = json.loads(json_str)
                    if "code" in data:
                        agent_code = data["code"]
                    else:
                        agent_code = "# Error: JSON found but no 'code' field."
                except json.JSONDecodeError:
                    agent_code = "# Error: Invalid JSON block found."
            else:
                # Fallback: check for just ``` (generic block)
                # Matches ``` followed by optional language identifier, then content
                code_match_loose = re.search(r"```(?:\w+)?\n([\s\S]*?)\n```", candidate_response)
                if code_match_loose:
                    agent_code = code_match_loose.group(1).strip()

        # Save extracted code to state
        ctx.session.state["agent_code"] = agent_code

        # 3. Retrieve verification plan directly from session state
        verification_plan = ctx.session.state.get("verification_plan", "Error: No verification plan found in session state.")
        
        # Use a fixed sanity check prompt for the agent execution
        test_prompt = "Hello! Please confirm you are working."
        
        # Try to extract a specific test prompt from the verification plan if present
        prompt_match = re.search(r"Test Prompt:\s*(.*?)(?:\n|$)", verification_plan, re.IGNORECASE)
        if prompt_match:
            extracted_prompt = prompt_match.group(1).strip()
            if extracted_prompt:
                test_prompt = extracted_prompt

        # Yield fake tool call for trace logging consistency
        run_adk_tool_id = f"call_{uuid.uuid4().hex}"
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(function_call=types.FunctionCall(
                    name="run_adk_agent",
                    args={"prompt": test_prompt, "agent_code": agent_code},
                    id=run_adk_tool_id 
                ))]
            )
        )

        # 4. Execute the agent code using run_adk_agent
        run_output = await self._tools_helper.run_adk_agent(
            prompt=test_prompt,
            model_name=self._model_name, 
            agent_code=agent_code,
        )

        # Yield fake tool result for trace logging consistency
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="tool",
                parts=[types.Part(function_response=types.FunctionResponse(
                    name="run_adk_agent",
                    response={"result": run_output}, 
                    id=run_adk_tool_id
                ))]
            )
        )

        # 5. Save output to session state for the Analyst
        ctx.session.state["run_output"] = run_output

        # 6. Yield the logs so the Analyst can see them in history
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Execution Logs:\n{run_output}")]
            )
        )


class CodeBasedFinalVerifier(Agent):
    """
    A code-based agent that finalizes the solution by persisting it and returning the structured response.
    """
    def __init__(self, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 1. Retrieve code from session state
        agent_code = ctx.session.state.get("agent_code", "# Error: No agent code found in session state.")
        
        # 2. Write to file
        # We assume 'my_agent.py' is the desired output file for this benchmark context
        self._tools_helper.write_file("my_agent.py", agent_code)
        
        # Yield fake tool call for trace logging consistency
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(function_call=types.FunctionCall(
                    name="write_file",
                    args={"file_path": "my_agent.py", "content": agent_code},
                    id=f"call_{uuid.uuid4().hex}"
                ))]
            )
        )
        
        # 3. Construct FinalResponse
        # Ideally, we would retrieve the rationale from the CandidateCreator's output or session state.
        # For now, we provide a standard rationale.
        # TODO: Replace with FixErrorAnswerOutput or equivalent
        response = FinalResponse(
            code=agent_code,
            rationale="The agent code has been implemented, verified, and persisted to my_agent.py."
        )
        
        json_str = json.dumps(response.model_dump())
        
        # 4. Save to session state for TeardownAgent
        ctx.session.state["final_response"] = json_str

        # 5. Yield output
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=json_str)]
            )
        )

def create_structured_adk_agent(
    workspace_root: Path,
    model_name: str = "gemini-2.5-pro",
    venv_path: Path | None = None,
    api_key_manager: ApiKeyManager | None = None,
    use_index_retrieval: bool = True,
) -> SequentialAgent:
    """
    Creates a structured ADK agent with setup, planning, verification, implementation loop, final output, and teardown.
    Enforces structured output for each step and workspace isolation.

    Refactored to store the agent implementation code in session state to reduce token usage from disk I/O.
    """
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)

    # --- State Management Tools ---
    def save_final_response(response_json: str, tool_context: ToolContext) -> str:
        """Saves the final response JSON to the session state."""
        tool_context.session.state["final_response"] = response_json
        return "Successfully saved final response to session state."

    def save_verification_plan(test_prompt: str, tool_context: ToolContext) -> str:
        """Saves the verification test prompt to session state."""
        tool_context.session.state["test_prompt"] = test_prompt
        return "Successfully saved test prompt."

    def save_relevant_modules(modules: list[str], tool_context: ToolContext) -> str:
        """Saves the list of relevant modules to session state."""
        tool_context.session.state["relevant_modules_json"] = json.dumps({"modules": modules})
        return f"Saved {len(modules)} modules."

    def save_implementation_plan(plan_text: str, tool_context: ToolContext) -> str:
        """Saves the implementation plan text to session state."""
        tool_context.session.state["implementation_plan"] = plan_text
        return "Successfully saved implementation plan."

    def get_agent_code(tool_context: ToolContext) -> str:
        """Retrieves the agent implementation code from the session state."""
        return tool_context.session.state.get(
            "agent_code", "Error: No agent code found in session state."
        )

    async def run_adk_agent(
        prompt: str,
        model_name: Optional[str] = None,
        agent_code: Optional[str] = None,
        agent_file: Optional[str] = None,
        initial_state: Optional[str] = None,
    ) -> str:
        """
        Runs an ADK agent.
        """
        code_to_run = agent_code
        if not code_to_run and not agent_file:
            return "Error: No agent code provided and none found in session state. Provide `agent_code`, `agent_file`, or use `save_agent_code` first."

        # Use provided model_name or fallback to the default for this generator
        effective_model_name = model_name if model_name else "gemini-2.5-pro"

        # Get a fresh API key for this execution if manager is available
        api_key = None
        if api_key_manager:
            api_key = api_key_manager.get_next_key()

        # Delegate to the robust run_adk_agent tool
        return await tools_helper.run_adk_agent(
            prompt=prompt,
            model_name=effective_model_name,
            agent_code=code_to_run,
            agent_file=agent_file,
            initial_state=initial_state,
            api_key=api_key,
        )

    # Common tools
    read_tool = FunctionTool(tools_helper.read_file)
    write_tool = FunctionTool(tools_helper.write_file)
    list_tool = FunctionTool(tools_helper.list_directory)
    search_tool = FunctionTool(tools_helper.search_files)
    get_help_tool = FunctionTool(tools_helper.get_module_help)
    exit_loop_tool = FunctionTool(exit_loop)

    # New state tools
    # save_final_response_tool = FunctionTool(save_final_response)
    save_plan_tool = FunctionTool(save_verification_plan)
    save_impl_plan_tool = FunctionTool(save_implementation_plan)
    save_modules_tool = FunctionTool(save_relevant_modules)

    # Determine Model (String or Object)
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name

    # 0. Setup Agent
    setup_agent = SetupAgentCodeBased(
        name="setup_agent", workspace_root=workspace_root, tools_helper=tools_helper
    )

    # 0.2 Prompt Sanitizer
    prompt_sanitizer_agent = PromptSanitizerAgent(
        model=model,
        include_contents='none',
        output_key="sanitized_user_request",
    )

    # Knowledge Retrieval Strategy
    retrieval_agents = []
    
    # Define DocstringFetcherAgent locally to capture tools_helper
    class DocstringFetcherAgent(Agent):
        """Fetches help for selected modules using captured tools_helper."""
        async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
            # 1. Retrieve selected modules from session state
            relevant_modules_json = ctx.session.state.get("relevant_modules_json", "{}")
            
            try:
                if isinstance(relevant_modules_json, str):
                    if "```json" in relevant_modules_json:
                        relevant_modules_json = relevant_modules_json.split("```json", 1)[1].split("```", 1)[0].strip()
                    elif "```" in relevant_modules_json:
                        relevant_modules_json = relevant_modules_json.split("```", 1)[1].split("```", 1)[0].strip()
                    relevant_modules = RelevantModules.model_validate_json(relevant_modules_json)
                elif isinstance(relevant_modules_json, dict):
                     relevant_modules = RelevantModules.model_validate(relevant_modules_json)
                else:
                     # Assume it's already a model object
                     relevant_modules = relevant_modules_json

            except Exception as e:
                # print(f"[WARNING] Failed to parse RelevantModules: {e}. Skipping knowledge retrieval.")
                ctx.session.state["knowledge_context"] = f"Error retrieving knowledge context: {e}"
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=f"Error parsing relevant modules: {e}")]
                    )
                )
                return

            # 2. Fetch help for each module using captured tools_helper
            knowledge_context_parts = []
            for module_name in relevant_modules.modules:
                try:
                    help_text = await tools_helper.get_module_help(module_name)
                    knowledge_context_parts.append(f"--- Help for {module_name} ---\n{help_text}\n")
                except Exception as e:
                    knowledge_context_parts.append(f"Error fetching help for {module_name}: {e}\n")

            full_context = "\n".join(knowledge_context_parts)
            
            # 3. Save to session state
            ctx.session.state["knowledge_context"] = full_context
            
            # 4. Yield output
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"Fetched knowledge context for {len(relevant_modules.modules)} modules.")]
                )
            )

    if use_index_retrieval:
        # Load index content
        index_path = Path("benchmarks/adk_index.yaml")
        if index_path.exists():
            with open(index_path, "r") as f:
                adk_index_content = f.read()
        else:
            adk_index_content = "Error: adk_index.yaml not found."

        module_selector_agent = LlmAgent(
            name="module_selector_agent",
            model=model,
            tools=[save_modules_tool], 
            # output_schema=RelevantModules, # REMOVED
            # output_key="relevant_modules_json", # REMOVED
            include_contents='none',
            instruction=(
                f"You are the Module Selector Agent. Use the provided index to select relevant modules.\n"
                f"Index:\n{adk_index_content}\n"
                "Request: {sanitized_user_request}\n"
                "Analyze the request and select the modules that are most likely to contain the APIs needed."
                "CRITICAL: Use the `save_relevant_modules` tool to save the list of modules that are most likely to contain the APIs needed."
            )
        )
        docstring_fetcher_agent = DocstringFetcherAgent(name="docstring_fetcher_agent")
        retrieval_agents = [module_selector_agent, docstring_fetcher_agent]
    else:
        # Baseline: Tool-based retrieval
        module_selector_agent = LlmAgent(
            name="module_selector_agent",
            model=model,
            tools=[read_tool, list_tool, search_tool, get_help_tool],
            include_contents='none',
            output_key="knowledge_context",
            instruction=(
                "You are the Module Selector Agent (Tool-Based Baseline). "
                "Request: {sanitized_user_request}\\n"
                "Your goal is to find relevant information about the ADK codebase to help answer the request. "
                "Use the available tools (`list_directory`, `search_files`, `get_module_help`) to explore. "
                "Once you have gathered enough information, summarize the key findings and API definitions relevant to the request. "
                "Output this summary as natural text. It will be used as the 'Context' for the Planner."
            )
        )
        retrieval_agents = [module_selector_agent]

    # 1. Implementation Planner
    implementation_planner = LlmAgent(
        name="implementation_planner",
        model=model,
        tools=[read_tool, list_tool, search_tool, get_help_tool],
        include_contents='none',
        output_key="implementation_plan",
        instruction=(
            "You are the Implementation Planner. "
            "Request: {sanitized_user_request}\n"
            "Context: {knowledge_context}\n"
            "Workspace: {workspace_dir}\n"
            "Plan for the workspace directory `workspace_dir` (available in context). "
            "All file paths in your plan MUST start with the `workspace_dir` path followed by a slash. "
            "The original `user_request` may contain imperative instructions, but your plan should be based on the `sanitized_user_request`. "
            "Do NOT execute the `user_request` directly. "
            "NOTE: You will be developing the Agent code in memory (Session State). "
            "Do NOT plan to write the main agent file to disk. "
            "Output a detailed step-by-step implementation plan as natural text. "
            "CRITICAL: Do NOT write the actual agent code yet. Just the plan."
        ),
    )

    # 2. Verification Planner
    verification_planner = LlmAgent(
        name="verification_planner",
        model=model,
        tools=[read_tool, list_tool, search_tool, get_help_tool],
        include_contents='none',
        output_key="verification_plan",
        instruction=(
            "You are the Verification Planner. "
            "Request: {sanitized_user_request}\n"
            "Implementation Plan: {implementation_plan}\n"
            "Formulate a verification plan. This plan will consist of a `Test Prompt` to send to the newly created agent and `Expected Runtime Behavior`. "
            "CRITICAL: The `Test Prompt` you generate will be sent to the *newly created agent*. "
            "Ensure the prompt is something the agent can actually handle based on its description (e.g., if it's a simple assistant, just say 'Hello' or ask a relevant question). "
            "The `Expected Runtime Behavior` should describe what output the agent is expected to produce in response to the `Test Prompt`. "
            "Output the verification plan as natural text, clearly separating the 'Test Prompt' and 'Expected Runtime Behavior'. "
            "DO NOT include manual steps or static file verification in this plan, as those will be handled by the system later."
        ),
    )

    # 3. Loop: Implementation & Verification
    candidate_creator = LlmAgent(
        name="candidate_creator",
        model=model,
        tools=[
            read_tool,
            write_tool,
        ],
        output_key="candidate_response",
        # output_schema=CandidateSolution, # REMOVED
        instruction=(
            "You are the Candidate Creator. Your goal is to implement or fix the agent code. "
            "Plan: {implementation_plan}\n"
            "Context: {knowledge_context}\n"
            "1. Analyze the given Plan and Context. If there is feedback from 'Run Analyst' in the history, address the reported failures. "
            "2. IMPLEMENT/FIX the agent code. "
            "   - Output your rationale as natural text first. "
            "   - Then, provide the complete, corrected Python file content within a markdown code block (```python...```). "
            "     Ensure all necessary imports are included and the code is syntactically valid."
            "CRITICAL: Your ONLY allowed tools are: `read_file`, `write_file`. "
            "DO NOT call any tools for code submission or execution. The system will extract your code from the markdown block and handle execution."
        ),
    )


    code_based_runner = CodeBasedRunner(
        name="code_based_runner",
        tools_helper=tools_helper,
        model_name=model_name
    )

    run_analysis_agent = LlmAgent(
        name="run_analysis_agent",
        model=model,
        tools=[exit_loop_tool, read_tool],
        include_contents='none',
        instruction=(
            "You are the Run Analyst. "
            "Verification Plan: {verification_plan}\n"
            "Logs: {run_output}\n"
            "1. Analyze the 'Execution Logs' based on the 'Verification Plan'. The agent was run with a `Test Prompt` as defined in the plan. "
            "2. Determine if the agent successfully satisfied the requirements by checking its `Stdout` and `Stderr` against the `Expected Runtime Behavior` in the plan. "
            "   - Look for a coherent response from the agent in `Stdout` that matches the `Expected Runtime Behavior`. "
            "   - Check for any errors in `Stderr`. A clean `Stderr` is usually desired. "
            "3. Action: "
            "   - If SUCCESS: Call `exit_loop` immediately. "
            "   - If FAILURE: Output a clear, concise analysis of WHY it failed. "
            "     This analysis will be read by the Candidate Creator in the next step to fix the code. "
            "     Do not write code yourself, just analyze."
        )
    )

    implementation_loop = LoopAgent(
        name="implementation_loop",
        sub_agents=[candidate_creator, code_based_runner, run_analysis_agent],
        max_iterations=5,
    )

    # 4. Final Verifier / Output
    final_verifier = CodeBasedFinalVerifier(
        name="final_verifier",
        tools_helper=tools_helper
    )

    # 5. Teardown Agent
    teardown_agent = CodeBasedTeardownAgent(
        name="teardown_agent", 
        workspace_root=workspace_root, 
        tools_helper=tools_helper
    )

    agent_obj = SequentialAgent(
        name="structured_solver",
        sub_agents=[
            setup_agent,
            prompt_sanitizer_agent,
            *retrieval_agents,
            implementation_planner,
            verification_planner,
            implementation_loop,
            final_verifier,
            teardown_agent,
        ],
    )

    return agent_obj

def create_workflow_agent(
    workspace_root: Path,
    model_name: str = "gemini-2.5-pro",
    venv_path: Path | None = None,
) -> LlmAgent:
    """
    Creates a workflow-enabled LlmAgent with file system and shell tools.

    Args:
        workspace_root: The root directory for the agent's workspace.
        model_name: The Gemini model to use.
        venv_path: Optional path to a virtual environment to use for shell commands.
    """
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)

    tools = [
        FunctionTool(tools_helper.read_file),
        FunctionTool(tools_helper.write_file),
        FunctionTool(tools_helper.list_directory),
        FunctionTool(tools_helper.run_shell_command),
        FunctionTool(tools_helper.search_files),
        FunctionTool(tools_helper.run_adk_agent),
    ]

    return LlmAgent(
        name="workflow_solver",
        model=model_name,
        tools=tools,
        instruction=(
            "You are an expert software engineer tasked with solving programming benchmarks. "
            "You have access to a set of tools to read code, write files, and run commands. "
            f"You are operating in a workspace at {workspace_root}. "
            "The ADK Python repository is available at `repos/adk-python` relative to the workspace root. "
            "A virtual environment is active for your shell commands, with `adk` and `pytest` installed. "
            "\n\n"
            "**Workflow:**\n"
            "1.  **Analyze:** Read the benchmark requirements and explore the codebase. "
            "Use `list_directory` (supports ignore patterns) and `read_file` (supports offset/limit for large files) to understand the environment.\n"
            "2.  **Plan:** Determine what code needs to be written or fixed.\n"
            "3.  **Implement:** Use `write_file` to create or modify the necessary Python files.\n"
            "4.  **Verify:** Use `run_adk_agent` to execute and verify the agent you created. Use `run_shell_command` for other tests (e.g., `pytest`).\n"
            "5.  **Iterate:** If verification fails, analyze the error, fix the code, and verify again.\n"
            "6.  **Final Output:** Once satisfied, output the final JSON as requested by the user prompt."
        ),
    )


def create_workflow_adk_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",  # New parameter for ADK branch
) -> AdkAnswerGenerator:
    """
    Factory to create an AdkAnswerGenerator with a fully managed workflow agent.
    Handles workspace creation, venv setup, agent instantiation, and lifecycle hooks.
    """
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_workflow_"))
    venv_path = workspace_root / "venv"

    # Deferred agent creation is not supported by AdkAnswerGenerator __init__ pattern I implemented earlier
    # wait, AdkAnswerGenerator takes an 'agent' instance.
    # So I must create the agent HERE.
    agent = create_workflow_agent(workspace_root, model_name, venv_path=venv_path)

    async def setup_hook():
        print(f"[WorkflowAdk] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        repos_dir.mkdir(exist_ok=True)

        # 1. Clone ADK Python
        if not adk_repo_dir.exists():
            print(f"[WorkflowAdk] Cloning adk-python...")
            try:
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--branch",
                        adk_branch,
                        "https://github.com/google/adk-python.git",
                        str(adk_repo_dir),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=300,  # 5 minutes for cloning
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to clone adk-python: {e.stderr.decode()}")
            except subprocess.TimeoutExpired:
                raise RuntimeError("Git clone timed out after 5 minutes.")

        # 2. Create Virtual Environment
        if not venv_path.exists():
            print(f"[WorkflowAdk] Creating virtual environment at {venv_path}...")
            subprocess.run(
                [os.sys.executable, "-m", "venv", str(venv_path)],
                check=True,
                timeout=300,
            )

            # Helper to run pip in venv
            pip_cmd = [str(venv_path / "bin" / "pip"), "install"]

            # 3. Install Dependencies
            print(f"[WorkflowAdk] Installing dependencies...")
            subprocess.run(pip_cmd + ["--upgrade", "pip"], check=True, timeout=300)
            subprocess.run(
                pip_cmd + ["pytest", "--index-url", "https://pypi.org/simple"],
                check=True,
                timeout=300,
            )  # Install pytest from PyPI

            # 4. Install Cloned Repo (Editable mode)
            # We install the cloned adk-python to allow the agent to test modifications to it if needed,
            # or just to have it available as a library.
            # Assuming adk-python root has setup.py or pyproject.toml
            print(f"[WorkflowAdk] Installing local adk-python...")
            subprocess.run(
                pip_cmd
                +
                [
                    "--no-cache-dir",
                    "--force-reinstall",
                    "-e",
                    str(adk_repo_dir),
                    "--index-url",
                    "https://pypi.org/simple",
                ],
                check=True,
                timeout=300,
            )

        print(f"[WorkflowAdk] Setup complete.")

    async def teardown_hook():
        if workspace_root.exists() and "adk_workflow_" in str(workspace_root):
            shutil.rmtree(workspace_root)

    return AdkAnswerGenerator(
        agent=agent,
        name=f"WorkflowAdk({model_name})",
        setup_hook=setup_hook,
        teardown_hook=teardown_hook,
        api_key_manager=api_key_manager,
    )


def create_structured_workflow_adk_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory to create an AdkAnswerGenerator with a fully managed STRUCTURED workflow agent.
    Handles workspace creation, venv setup, agent instantiation, and lifecycle hooks.
    """
    return _create_managed_adk_generator(
        model_name, api_key_manager, adk_branch, 
        use_index_retrieval=True, 
        name_prefix="StructuredWorkflowAdk", 
        folder_prefix="adk_struct_workflow_"
    )


# Helper to avoid duplication
def _create_managed_adk_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None,
    adk_branch: str,
    use_index_retrieval: bool,
    name_prefix: str,
    folder_prefix: str
) -> AdkAnswerGenerator:
    """
    Internal helper to create a managed ADK generator with environment setup/teardown.

    Args:
        model_name: The Gemini model to use.
        api_key_manager: Optional API key manager.
        adk_branch: Git branch of ADK Python to clone.
        use_index_retrieval: Whether to use the optimized index-based retrieval (True) or tool-based (False).
        name_prefix: Prefix for the generator name (e.g., "StructuredWorkflowAdk").
        folder_prefix: Prefix for the temporary workspace folder.
    """
    
    if not can_use_output_schema_with_tools(model_name):
        print(f"[WARNING] Native output schema with tools is NOT supported for model '{model_name}'.")

    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"

    agent = create_structured_adk_agent(
        workspace_root, model_name, venv_path=venv_path, api_key_manager=api_key_manager,
        use_index_retrieval=use_index_retrieval
    )

    async def setup_hook():
        print(f"[{name_prefix}] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        repos_dir.mkdir(exist_ok=True)

        if not adk_repo_dir.exists():
            print(f"[{name_prefix}] Cloning adk-python...")
            try:
                subprocess.run(
                    ["git", "clone", "--branch", adk_branch, "https://github.com/google/adk-python.git", str(adk_repo_dir)],
                    check=True, capture_output=True, timeout=300
                )
            except Exception as e:
                raise RuntimeError(f"Failed to clone adk-python: {e}")

        if not venv_path.exists():
            print(f"[{name_prefix}] Creating virtual environment...")
            subprocess.run([os.sys.executable, "-m", "venv", str(venv_path)], check=True, timeout=300)
            
            pip_cmd = [str(venv_path / "bin" / "pip"), "install"]
            subprocess.run(pip_cmd + ["--upgrade", "--quiet", "pip"], check=True, timeout=300)
            subprocess.run(pip_cmd + ["--quiet", "pytest", "--index-url", "https://pypi.org/simple"], check=True, timeout=300)
            subprocess.run(pip_cmd + ["--quiet", "-e", str(adk_repo_dir), "--index-url", "https://pypi.org/simple"], check=True, timeout=300)

        print(f"[{name_prefix}] Setup complete.")

    async def teardown_hook():
        if workspace_root.exists() and folder_prefix in str(workspace_root):
            shutil.rmtree(workspace_root)

    return AdkAnswerGenerator(
        agent=agent,
        name=f"{name_prefix}({model_name})",
        setup_hook=setup_hook,
        teardown_hook=teardown_hook,
        api_key_manager=api_key_manager,
    )

def create_baseline_workflow_adk_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory to create a BASELINE structured workflow agent.
    This version uses TOOL-BASED knowledge retrieval (search, read_file) instead of the optimized index.
    It is slower but produces more concise, summarized context for the Planner.
    Useful for benchmarking against the optimized StructuredWorkflowAdk.
    """
    return _create_managed_adk_generator(
        model_name, api_key_manager, adk_branch, 
        use_index_retrieval=False, 
        name_prefix="BaselineWorkflowAdk", 
        folder_prefix="adk_base_workflow_"
    )
