"""
Verifier Agents for Question Quality Verification.
"""
from pathlib import Path
import json
from typing import Optional, AsyncGenerator
import uuid
import tempfile
import shutil
import os
import subprocess
import re

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent, Agent, InvocationContext
from google.adk.events import Event
from google.adk.tools import FunctionTool, exit_loop
from google.genai import types

from benchmarks.answer_generators.adk_agents import (
    SetupAgentCodeBased,
    CodeBasedTeardownAgent,
    RotatingKeyGemini,
    DEFAULT_MODEL_NAME,
    AdkAnswerGenerator
)
from benchmarks.answer_generators.adk_tools import AdkTools
from core.api_key_manager import ApiKeyManager


class ClaimAnalystAgent(LlmAgent):
    """
    Analyzes the question and decomposes it into testable claims.
    """
    def __init__(self, model, tools_helper):
        tools = [
            FunctionTool(tools_helper.search_ranked_targets),
            FunctionTool(tools_helper.inspect_fqn),
            FunctionTool(tools_helper.read_file),
            FunctionTool(tools_helper.search_files),
        ]
        
        super().__init__(
            name="claim_analyst",
            model=model,
            tools=tools,
            output_key="claims_json",  # Save output to session state
            instruction=(
                "You are a Senior QA Analyst. Your task is to audit a benchmark question.\n"
                "Input: A Multiple Choice Question with options.\n"
                "Goal: Decompose each option into a specific, testable hypothesis (Claim).\n"
                "\n"
                "Process:\n"
                "1. Research the codebase using `search_ranked_targets` or `inspect_fqn` to understand the relevant classes and methods.\n"
                "   - Verify if the classes/methods mentioned in the question even exist.\n"
                "2. For EACH option (A, B, C, D...), formulate a hypothesis.\n"
                "   - Positive Claim: 'Option A implies code X runs successfully'.\n"
                "   - Negative Claim: 'Option B implies code Y raises ValidationError'.\n"
                "3. Output a JSON list of claim objects to `session.state.claims_json` (wrapped in markdown json block).\n"
                "   Format: `[{\\\"option\\\": \\\"A\\\", \\\"hypothesis\\\": \\\"...\\\", \\\"code_hint\\\": \\\"...\\\"}, ...]`\n"
                "\n"
                "CRITICAL: Do not try to solve the question yet. Just define what needs to be proved.\n"
                "Provide a brief rationale before the JSON."
            )
        )

class ProofEngineerAgent(LlmAgent):
    """
    Writes and executes pytest scripts to prove claims.
    """
    def __init__(self, model, tools_helper):
        tools = [
            FunctionTool(tools_helper.write_file),
            FunctionTool(tools_helper.run_shell_command),
            FunctionTool(tools_helper.read_file),
            FunctionTool(tools_helper.read_full_execution_logs),
            FunctionTool(exit_loop),
        ]
        
        super().__init__(
            name="proof_engineer",
            model=model,
            tools=tools,
            include_contents="default",
            output_key="engineer_log",
            instruction=(
                "You are a Proof Engineer. You have a list of Claims in `session.state.claims_json` (look at previous turns or extract from history).\n"
                "Your goal is to empirically PROVE whether each claim is True or False using `pytest`.\n"
                "\n"
                "Process:\n"
                "1. Pick an unproven claim from the list.\n"
                "2. Write a standalone `pytest` file (e.g., `test_option_A.py`).\n"
                "   - Use `pytest.raises(...)` if you expect an error.\n"
                "   - Use assertions if you expect success.\n"
                "   - IMPORTANT: Mock external calls if necessary. Use `unittest.mock`.\n"
                "3. Execute: `run_shell_command('pytest test_option_A.py', description='Verifying that Option A initializes correctly')`.\n"
                "   - CRITICAL: You MUST provide a natural language `description` in the `run_shell_command` call explaining EXACTLY what this test proves.\n"
                "4. Analyze the result. Did the test PASS (proving the claim) or FAIL?\n"
                "   - Note: If a Negative Claim (expecting error) PASSES, it means the error WAS raised, so the claim is TRUE.\n"
                "5. Repeat until ALL claims are tested.\n"
                "   - CRITICAL: DO NOT DELETE the `pytest` files or any other generated scripts. They must remain in the workspace for archival.\n"
                "6. Once all claims are tested, output a summary of results and call `exit_loop()`."
            )
        )

class VerdictSynthesizerAgent(LlmAgent):
    """
    Synthesizes the final verdict based on proof results.
    """
    def __init__(self, model):
        super().__init__(
            name="verdict_synthesizer",
            model=model,
            tools=[],
            output_key="final_response",
            instruction=(
                "You are the Verdict Synthesizer.\n"
                "Input: Original Question, Ground Truth, and Empirical Proof Results (review conversation history).\n"
                "Task: Determine the quality of the question.\n"
                "\n"
                "Logic:\n"
                "- VALID: The 'Correct' option was proven valid (code works), AND all 'Distractor' options were proven invalid (code fails or raises error).\n"
                "- AMBIGUOUS: Multiple options were proven valid (distractors failed to fail).\n"
                "- INCORRECT: The 'Correct' option failed (code did not work).\n"
                "\n"
                "Output: A JSON report:\n"
                "```json\n"
                "{\n"
                "  \"verdict\": \"Valid|Ambiguous|Incorrect\",\n"
                "  \"details\": \"...\",\n"
                "  \"suggested_fix\": \"...\" (if needed)\n"
                "}\n"
                "```"
            )
        )

def create_verifier_adk_generator(
    model_name: str = DEFAULT_MODEL_NAME,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Creates an AdkAnswerGenerator for verifying benchmarks.
    """
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_verifier_"))
    venv_path = workspace_root / "venv"
    
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name
        
    setup_agent = SetupAgentCodeBased(
        name="setup_agent",
        workspace_root=tools_helper.workspace_root,
        tools_helper=tools_helper,
    )
    
    claim_analyst = ClaimAnalystAgent(model, tools_helper)
    
    proof_engineer = ProofEngineerAgent(model, tools_helper)
    
    proof_loop = LoopAgent(
        name="proof_loop",
        sub_agents=[proof_engineer],
        max_iterations=8 # Sufficient for 4 options * 2 turns
    )
    
    verdict_synthesizer = VerdictSynthesizerAgent(model)
    
    teardown_agent = CodeBasedTeardownAgent(
        name="teardown_agent",
        workspace_root=tools_helper.workspace_root,
        tools_helper=tools_helper,
    )
    
    verifier_agent = SequentialAgent(
        name="verifier_pipeline",
        sub_agents=[
            setup_agent,
            claim_analyst,
            proof_loop,
            verdict_synthesizer
            # teardown_agent removed to preserve artifacts for archival
        ]
    )
    
    async def setup_hook():
        print(f"[Verifier] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        repos_dir.mkdir(exist_ok=True)

        if not adk_repo_dir.exists():
            print(f"[Verifier] Cloning adk-python...")
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
                    timeout=300,
                )
            except Exception as e:
                # If git fails (e.g. no network), we might want to error out or assume local dev
                raise RuntimeError(f"Failed to clone adk-python: {e}")

        if not venv_path.exists():
            print(f"[Verifier] Creating virtual environment...")
            subprocess.run(
                [os.sys.executable, "-m", "venv", str(venv_path)],
                check=True,
                timeout=300,
            )

            pip_cmd = [str(venv_path / "bin" / "pip"), "install"]
            # Install pytest
            subprocess.run(
                pip_cmd + ["--upgrade", "--quiet", "pip"], check=True, timeout=300
            )
            subprocess.run(
                pip_cmd
                + ["--quiet", "pytest", "pytest-asyncio", "--index-url", "https://pypi.org/simple"],
                check=True,
                timeout=300,
            )
            # Install ADK in editable mode
            subprocess.run(
                pip_cmd
                + [
                    "--quiet",
                    "-e",
                    str(adk_repo_dir),
                    "--index-url",
                    "https://pypi.org/simple",
                ],
                check=True,
                timeout=300,
            )

        print(f"[Verifier] Setup complete.")

    async def teardown_hook():
        if workspace_root.exists() and "adk_verifier_" in str(workspace_root):
            shutil.rmtree(workspace_root)
            
    return AdkAnswerGenerator(
        agent=verifier_agent,
        name=f"Verifier({model_name})",
        setup_hook=setup_hook,
        teardown_hook=teardown_hook,
        api_key_manager=api_key_manager
    )
