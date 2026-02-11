from typing import Optional, List
from pathlib import Path
import tempfile
import subprocess
import os
import shutil

from google.adk.agents import SequentialAgent
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, CodeBasedTeardownAgent, RotatingKeyGemini, DEFAULT_MODEL_NAME, AdkAnswerGenerator
from benchmarks.answer_generators.adk_tools import AdkTools
from core.api_key_manager import ApiKeyManager

from .base import VerdictSynthesizerAgent
from .multiple_choice import build_multiple_choice_pipeline
from .fix_errors import build_fix_errors_pipeline

def create_verifier_adk_generator(
    model_name: str = DEFAULT_MODEL_NAME,
    api_key_manager: Optional[ApiKeyManager] = None,
    adk_branch: str = "v1.20.0",  # Retained for backwards compatibility
    benchmark_type: str = "multiple_choice",
    target_repo_url: str = "https://github.com/google/adk-python.git",
    target_repo_version: str = "v1.20.0",
    extra_dependencies: Optional[List[str]] = None
) -> AdkAnswerGenerator:
    """
    Creates an AdkAnswerGenerator for verifying benchmarks polymorphically.
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
    
    teardown_agent = CodeBasedTeardownAgent(
        name="teardown_agent",
        workspace_root=tools_helper.workspace_root,
        tools_helper=tools_helper,
    )
    
    verdict_synthesizer = VerdictSynthesizerAgent(model)
    
    # Polymorphic Pipeline Router
    if benchmark_type == "multiple_choice":
        dynamic_pipeline = build_multiple_choice_pipeline(model, tools_helper)
    elif benchmark_type == "fix_errors":
        dynamic_pipeline = build_fix_errors_pipeline(model, tools_helper)
    elif benchmark_type == "api_understanding":
        # Placeholder for future expansion
        dynamic_pipeline = []
    else:
        print(f"Warning: unsupported benchmark type {benchmark_type}, defaulting to empty verification.")
        dynamic_pipeline = []

    verifier_agent = SequentialAgent(
        name="verifier_pipeline",
        sub_agents=[
            setup_agent,
            *dynamic_pipeline,
            verdict_synthesizer
            # teardown_agent removed to preserve artifacts for archival
        ]
    )
    
    async def setup_hook():
        print(f"[Verifier] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        
        # Deduce repo name from URL if possible
        repo_name = target_repo_url.split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
            
        # Hardcode correct PyPI metadata name for the ADK since github URL differs
        if repo_name == "adk-python":
            repo_name = "google-adk"
            
        if not repo_name:
            repo_name = "target-repo"

        # Fallback to adk_branch if target_repo_version not overridden, for backwards compatibility
        version_to_use = target_repo_version if target_repo_version != "v1.20.0" else adk_branch

        if not venv_path.exists():
            print(f"[Verifier] Structuring pyproject.toml and syncing via uv...")
            
            # 1. Build a dynamic pyproject.toml mapping the target via uv natively
            pyproject_content = f"""[project]
name = "adk-verifier-sandbox"
version = "0.1.0"
description = "Ephemeral verification environment"
requires-python = ">=3.11"
dependencies = [
    "pytest",
    "pytest-asyncio",
]
"""

            # We directly bind uv to the central remote repo branch, no cloning required!
            if target_repo_url.startswith("http"):
                repo_dep = f'{repo_name} @ git+{target_repo_url}@{version_to_use}'
            else:
                # If they passed a pure local directory path instead of a git URL
                repo_dep = f'{repo_name} @ file://{target_repo_url}'

            pyproject_content = pyproject_content.replace(
                '"pytest-asyncio",', 
                f'"pytest-asyncio",\n    "{repo_dep}",'
            )
            if extra_dependencies:
                deps_str = ',\n    '.join(f'"{dep}"' for dep in extra_dependencies)
                pyproject_content = pyproject_content.replace(
                    '"pytest-asyncio",', 
                    f'"pytest-asyncio",\n    {deps_str},'
                )

            pyproject_path = workspace_root / "pyproject.toml"
            pyproject_path.write_text(pyproject_content)

            # 2. Run `uv sync` to natively resolve, build the venv, and install everything in milliseconds
            env = os.environ.copy()
            # Note: We must restrict uv from bubbling up to the git repo root's pyproject
            env["UV_PROJECT_ENVIRONMENT"] = str(venv_path) 
            env["UV_DEFAULT_INDEX"] = "https://pypi.org/simple"
            env.pop("PIP_INDEX_URL", None)
            env.pop("PIP_EXTRA_INDEX_URL", None)
            env.pop("UV_INDEX_URL", None)
            env.pop("UV_EXTRA_INDEX_URL", None) 
            
            try:
                subprocess.run(
                    ["uv", "sync"],
                    check=True,
                    cwd=str(workspace_root),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            except subprocess.CalledProcessError as e:
                print(f"UV Sync Failed Output: {e.stdout}\n{e.stderr}")
                raise RuntimeError(f"uv sync failed during environment isolation: {e}")

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
