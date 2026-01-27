"""
Shared setup utilities for ADK benchmarking agents.
Handles workspace creation, git cloning, and virtual environment setup.
"""

import os
import subprocess
from pathlib import Path
from typing import Callable, Coroutine, Any


def create_standard_setup_hook(
    workspace_root: Path,
    adk_branch: str = "v1.20.0",
    name_prefix: str = "ADK_Agent",
) -> Callable[[], Coroutine[Any, Any, None]]:
    """
    Creates a standard async setup hook for ADK agents.

    This hook:
    1. Creates the workspace directories.
    2. Clones the ADK Python repository (if not present).
    3. Creates a virtual environment (if not present).
    4. Installs dependencies (pip, pytest, and the local ADK repo).
    """

    async def setup_hook():
        print(f"[{name_prefix}] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        repos_dir.mkdir(exist_ok=True)
        venv_path = workspace_root / "venv"

        # 1. Clone ADK Python
        if not adk_repo_dir.exists():
            local_cache = Path("../adk-python").resolve()
            if local_cache.exists():
                print(
                    f"[{name_prefix}] Using local adk-python cache from {local_cache}"
                )
                subprocess.run(
                    ["git", "clone", "--local", str(local_cache), str(adk_repo_dir)],
                    check=True,
                    capture_output=True,
                )
                # Ensure we are on the right branch
                subprocess.run(
                    ["git", "checkout", adk_branch],
                    cwd=str(adk_repo_dir),
                    check=True,
                    capture_output=True,
                )
            else:
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
                )

        # 2. Create Virtual Environment & Install Dependencies
        if not venv_path.exists():
            subprocess.run(
                [os.sys.executable, "-m", "venv", str(venv_path)], check=True
            )
            pip_cmd = [str(venv_path / "bin" / "pip"), "install"]

            # Upgrade pip
            subprocess.run(pip_cmd + ["--upgrade", "--quiet", "pip"], check=True)

            # Install pytest and other tools
            subprocess.run(
                pip_cmd
                + [
                    "--quiet",
                    "pytest",
                    "PyYAML",
                    "--index-url",
                    "https://pypi.org/simple",
                ],
                check=True,
            )

            # Install local ADK repo in editable mode
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
            )

    return setup_hook
