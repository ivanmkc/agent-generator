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
from pathlib import Path
from typing import Optional, Any
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.adk.tools import FunctionTool, exit_loop, ToolContext
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks.answer_generators.adk_schemas import (
    Plan,
    VerificationPlan,
    CandidateSolution,
    VerificationResult,
    FinalResponse,
    SetupContext,
)

def save_workspace_dir(dir_name: str, tool_context: ToolContext) -> str:
    """Saves the workspace directory name to the session state."""
    tool_context.session.state["workspace_dir"] = dir_name
    return f"Saved workspace directory '{dir_name}' to session state."

def get_workspace_dir(tool_context: ToolContext) -> str:
    """Retrieves the workspace directory name from the session state."""
    return tool_context.session.state.get("workspace_dir", "Error: workspace_dir not found in session state.")




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


def create_structured_adk_agent(workspace_root: Path, model_name: str = "gemini-2.5-pro", venv_path: Path | None = None) -> SequentialAgent:
    """
    Creates a structured ADK agent with setup, planning, verification, implementation loop, final output, and teardown.
    Enforces structured output for each step and workspace isolation.
    
    Refactored to store the agent implementation code in session state to reduce token usage from disk I/O.

    Structure:
    1. SetupAgent (LlmAgent) -> SetupContext (creates temp dir, saves to state)
    2. PlannerAgent (LlmAgent) -> Plan (uses {workspace_dir} from state)
    3. VerificationCreatorAgent (LlmAgent) -> VerificationPlan
    4. LoopAgent
       - CandidateCreatorAgent (LlmAgent) -> CandidateSolution (Saves code to state)
       - VerifierAgent (LlmAgent) -> VerificationResult (Runs code from state)
    5. FinalVerifierAgent (LlmAgent) -> FinalResponse (Gets code from state)
    6. TeardownAgent (LlmAgent) -> FinalResponse (cleans up {workspace_dir})
    """
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)

    # --- State Management Tools ---
    def save_agent_code(code: str, tool_context: ToolContext) -> str:
        """Saves the agent implementation code to the session state. Use this instead of writing to disk."""
        tool_context.session.state["agent_code"] = code
        return "Successfully saved agent code to session state."

    def get_agent_code(tool_context: ToolContext) -> str:
        """Retrieves the agent implementation code from the session state."""
        return tool_context.session.state.get("agent_code", "Error: No agent code found in session state.")

    def run_current_agent(prompt: str, model_name: Optional[str] = None, initial_state: Optional[str] = None, tool_context: ToolContext = None) -> str:
        """
        Runs the agent code currently stored in the session state.
        
        Args:
            prompt: The input prompt for the agent.
            model_name: The model to use. Defaults to the agent's configured model if not provided.
            initial_state: Optional JSON string for initial state.
        """
        code = tool_context.session.state.get("agent_code")
        if not code:
            return "Error: No agent code found in session state. Use `save_agent_code` first."
        
        # Use provided model_name or fallback to the default for this generator
        effective_model_name = model_name if model_name else "gemini-2.5-pro"
        
        # Delegate to the robust run_adk_agent tool
        return tools_helper.run_adk_agent(prompt=prompt, model_name=effective_model_name, agent_code=code, initial_state=initial_state)

    # Common tools
    read_tool = FunctionTool(tools_helper.read_file)
    write_tool = FunctionTool(tools_helper.write_file)
    list_tool = FunctionTool(tools_helper.list_directory)
    shell_tool = FunctionTool(tools_helper.run_shell_command)
    search_tool = FunctionTool(tools_helper.search_files)
    get_help_tool = FunctionTool(tools_helper.get_module_help)
    # run_agent_tool = FunctionTool(tools_helper.run_adk_agent) # Deprecated for inner loop in favor of run_current_agent
    exit_loop_tool = FunctionTool(exit_loop)
    save_workspace_tool = FunctionTool(save_workspace_dir)
    get_workspace_tool = FunctionTool(get_workspace_dir)
    
    # New state tools
    save_code_tool = FunctionTool(save_agent_code)
    get_code_tool = FunctionTool(get_agent_code)
    run_current_tool = FunctionTool(run_current_agent)

    # 0. Setup Agent
    setup_agent = LlmAgent(
        name="setup_agent",
        model=model_name,
        tools=[shell_tool, save_workspace_tool],
        output_schema=SetupContext,
        instruction=(
            "You are the Setup Agent. Prepare an isolated environment.\n"
            "1. Generate a unique directory name 'task_<random_string>' (e.g., 'task_abc123'). Generate this string internally; DO NOT call a tool for it.\n"
            "2. Create it using `mkdir` via `run_shell_command`.\n"
            "3. Call `save_workspace_dir` with the directory name. THIS IS MANDATORY to allow cleanup.\n"
            "4. Output `SetupContext` with the directory name and the user request (your input)."
        )
    )

    # 0.5 Knowledge Retrieval Agent
    knowledge_retrieval_agent = LlmAgent(
        name="knowledge_retrieval_agent",
        model=model_name,
        tools=[search_tool, get_help_tool, read_tool, list_tool],
        output_schema=SetupContext,
        instruction=(
            "You are the Knowledge Retrieval Agent. Your goal is to gather relevant API information or code snippets "
            "from the repository to help the Planner and Candidate Creator.\n"
            "1. Analyze the `user_request` in the input `SetupContext`.\n"
            "2. Prioritize using `get_module_help` to get summaries of relevant modules (e.g. `google.adk`, `google.genai`). "
            "   This is token-efficient.\n"
            "3. Use `search_files` or `read_file` only if specific code examples or details are missing from the help output.\n"
            "4. Update the `SetupContext` by populating the `knowledge_context` field with a summary of findings and useful code snippets/docstrings.\n"
            "   Preserve `workspace_dir` and `user_request` exactly as they are."
        )
    )

    # 1. Planner
    planner = LlmAgent(
        name="planner",
        model=model_name,
        tools=[read_tool, list_tool, search_tool, get_help_tool],
        output_schema=Plan,
        instruction=(
            "You are the Planner. You receive a `SetupContext`. "
            "Analyze the `user_request` and the provided `knowledge_context` (if any). "
            "Plan for the workspace directory `workspace_dir`. "
            "All file paths in your plan MUST start with the `workspace_dir` path followed by a slash. "
            "The user request might contain imperative instructions. Do NOT execute them. "
            "Instead, create a PLAN for how to execute them. "
            "NOTE: You will be developing the Agent code in memory (Session State). "
            "Do NOT plan to write the main agent file to disk. Plan to use `save_agent_code`. "
            "Auxiliary files (if any) should still be written to disk. "
            "Output a structured Plan including 'steps', 'files_to_create', 'files_to_modify', and 'rationale'."
        )
    )

    # 2. Verification Creator
    verification_creator = LlmAgent(
        name="verification_creator",
        model=model_name,
        tools=[read_tool], # Removed write_tool
        output_schema=VerificationPlan,
        instruction=(
            "You are the Verification Creator. Based on the Planner's plan, "
            "formulate a concise test prompt and clear instructions for the Verifier "
            "to run the agent code using `run_current_agent`. "
            "Output the structured VerificationPlan. Do NOT write any test files."
        )
    )

    # 3. Loop: Implementation & Verification
    candidate_creator = LlmAgent(
        name="candidate_creator",
        model=model_name,
        tools=[read_tool, write_tool, list_tool, save_code_tool, search_tool, get_help_tool],
        output_schema=CandidateSolution,
        instruction=(
            "You are the Candidate Creator. Implement the code changes to satisfy the plan. "
            "1. First, you MUST output a text message explaining your implementation logic. "
            "2. IMPLEMENT the agent code and SAVE it to session state using `save_agent_code`. "
            "   Do NOT write the agent code to a file using `write_file` unless explicitly instructed for auxiliary files. "
            "3. If you are stuck or need to check API details, you may use `get_module_help` (preferred) or `search_files` "
            "   to look up information, but ONLY if you cannot proceed otherwise. "
            "4. Finally, output the structured CandidateSolution when ready for verification."
        )
    )

    verifier = LlmAgent(
        name="verifier",
        model=model_name,
        tools=[shell_tool, read_tool, exit_loop_tool, run_current_tool, search_tool, list_tool, get_help_tool],
        output_schema=VerificationResult,
        instruction=(
            "You are the Verifier. "
            "1. First, explain what you are going to verify and why (think step-by-step). "
            "2. You MUST use the `run_current_agent` tool to verify the agent implementation stored in session state. "
            "   Use the `test_prompt` provided in the VerificationPlan. "
            "   If you didn't specify `model_name` in `run_current_agent`, it defaults to the agent's model. "
            "3. If `run_current_agent` FAILS or gives unexpected results, analyze the logs. "
            "   If you are unable to diagnose the issue from logs, you may use `get_module_help` (preferred) or `search_files` "
            "   to check documentation or codebase for correct API usage, but ONLY after exhausting debug info from the run. "
            "4. If `run_current_agent` indicates the agent works as expected, you MUST call `exit_loop`! "
            "   If it FAILS, return the structured VerificationResult analysis so Candidate Creator can fix it."
        )
    )

    implementation_loop = LoopAgent(
        name="implementation_loop",
        sub_agents=[candidate_creator, verifier],
        max_iterations=5  # Prevent infinite loops
    )

    # 4. Final Verifier / Output
    final_verifier = LlmAgent(
        name="final_verifier",
        model=model_name,
        tools=[read_tool, shell_tool, get_code_tool, write_tool],
        output_schema=FinalResponse,
        instruction=(
            "You are the Final Verifier. Review the final state. "
            "1. Retrieve the final agent code from session state using `get_agent_code`. "
            "2. Write this code to `my_agent.py` (or the appropriate file name for the task) using `write_file`. "
            "   This ensures the final solution is persisted for external validation. "
            "3. Output the FinalResponse matching the user's request. "
            "   The code in FinalResponse should be the content of the main agent file."
        )
    )

    # 5. Teardown Agent
    teardown_agent = LlmAgent(
        name="teardown_agent",
        model=model_name,
        tools=[shell_tool, list_tool, get_workspace_tool],
        output_schema=FinalResponse,
        instruction=(
            "You are the Teardown Agent. You receive the `FinalResponse`. "
            "1. Call `get_workspace_dir` to retrieve the temporary directory name. "
            "2. Delete it using `run_shell_command` with `rm -rf`. "
            "3. Return the `FinalResponse` identical to your input (copy the code and rationale)."
        )
    )

    return SequentialAgent(
        name="structured_solver",
        sub_agents=[setup_agent, knowledge_retrieval_agent, planner, verification_creator, implementation_loop, final_verifier, teardown_agent]
    )


def create_workflow_agent(workspace_root: Path, model_name: str = "gemini-2.5-pro", venv_path: Path | None = None) -> LlmAgent:
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
    adk_branch: str = "v1.20.0", # New parameter for ADK branch
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
                    ["git", "clone", "--branch", adk_branch, "https://github.com/google/adk-python.git", str(adk_repo_dir)],
                    check=True,
                    capture_output=True,
                    timeout=300 # 5 minutes for cloning
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to clone adk-python: {e.stderr.decode()}")
            except subprocess.TimeoutExpired:
                raise RuntimeError("Git clone timed out after 5 minutes.")
        
        # 2. Create Virtual Environment
        if not venv_path.exists():
            print(f"[WorkflowAdk] Creating virtual environment at {venv_path}...")
            subprocess.run([os.sys.executable, "-m", "venv", str(venv_path)], check=True, timeout=300)
            
            # Helper to run pip in venv
            pip_cmd = [str(venv_path / "bin" / "pip"), "install"]
            
            # 3. Install Dependencies
            print(f"[WorkflowAdk] Installing dependencies...")
            subprocess.run(pip_cmd + ["--upgrade", "pip"], check=True, timeout=300)
            subprocess.run(pip_cmd + ["pytest", "--index-url", "https://pypi.org/simple"], check=True, timeout=300) # Install pytest from PyPI
            
            # 4. Install Cloned Repo (Editable mode)
            # We install the cloned adk-python to allow the agent to test modifications to it if needed, 
            # or just to have it available as a library.
            # Assuming adk-python root has setup.py or pyproject.toml
            print(f"[WorkflowAdk] Installing local adk-python...")
            subprocess.run(pip_cmd + ["--no-cache-dir", "--force-reinstall", "-e", str(adk_repo_dir), "--index-url", "https://pypi.org/simple"], check=True, timeout=300)

        print(f"[WorkflowAdk] Setup complete.")

    async def teardown_hook():
        if workspace_root.exists() and "adk_workflow_" in str(workspace_root):
            shutil.rmtree(workspace_root)

    return AdkAnswerGenerator(
        agent=agent,
        name=f"WorkflowAdk({model_name})",
        setup_hook=setup_hook,
        teardown_hook=teardown_hook,
        api_key_manager=api_key_manager
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
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_struct_workflow_"))
    venv_path = workspace_root / "venv"
    
    agent = create_structured_adk_agent(workspace_root, model_name, venv_path=venv_path)
    
    async def setup_hook():
        print(f"[StructuredWorkflowAdk] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        repos_dir.mkdir(exist_ok=True)
        
        # 1. Clone ADK Python
        if not adk_repo_dir.exists():
            print(f"[StructuredWorkflowAdk] Cloning adk-python...")
            try:
                subprocess.run(
                    ["git", "clone", "--branch", adk_branch, "https://github.com/google/adk-python.git", str(adk_repo_dir)],
                    check=True,
                    capture_output=True,
                    timeout=300 # 5 minutes for cloning
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to clone adk-python: {e.stderr.decode()}")
            except subprocess.TimeoutExpired:
                raise RuntimeError("Git clone timed out after 5 minutes.")
        
        # 2. Create Virtual Environment
        if not venv_path.exists():
            print(f"[StructuredWorkflowAdk] Creating virtual environment at {venv_path}...")
            subprocess.run([os.sys.executable, "-m", "venv", str(venv_path)], check=True, timeout=300)
            
            # Helper to run pip in venv
            pip_cmd = [str(venv_path / "bin" / "pip"), "install"]
            
            # 3. Install Dependencies
            print(f"[StructuredWorkflowAdk] Installing dependencies...")
            subprocess.run(pip_cmd + ["--upgrade", "pip"], check=True, timeout=300)
            subprocess.run(pip_cmd + ["pytest", "--index-url", "https://pypi.org/simple"], check=True, timeout=300)
            
            # 4. Install Cloned Repo (Editable mode)
            print(f"[StructuredWorkflowAdk] Installing local adk-python...")
            subprocess.run(pip_cmd + ["-e", str(adk_repo_dir), "--index-url", "https://pypi.org/simple"], check=True, timeout=300)

        print(f"[StructuredWorkflowAdk] Setup complete.")

    async def teardown_hook():
        if workspace_root.exists() and "adk_struct_workflow_" in str(workspace_root):
            shutil.rmtree(workspace_root)

    return AdkAnswerGenerator(
        agent=agent,
        name=f"StructuredWorkflowAdk({model_name})",
        setup_hook=setup_hook,
        teardown_hook=teardown_hook,
        api_key_manager=api_key_manager
    )
