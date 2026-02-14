import pytest
import os
import subprocess
import json
import uuid
import tempfile
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner
from adk_knowledge_ext import manage_mcp

# Tests the Codebase Knowledge MCP Server's dynamic clone capability via the CLI

@pytest.mark.asyncio
async def test_read_source_code_dynamic_clone():
    """
    Verifies that read_source_code works (triggering dynamic cloning if needed).
    Runs against the local uvx extension to test the 'adk-python-v1.20.0' public repo.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY is required to test dynamic clone via Gemini CLI.")

    prompt = (
        "Please read the source code for the class `google.adk.agents.base_agent.BaseAgent` "
        "using the `read_source_code` tool. I need to see the class definition. "
        "Use kb_id='custom/adk-python@v1.20.0'."
    )
    
    # Create an isolated temporary workspace for the CLI to use with the MCP server
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # 1. Setup the MCP Server configuration for the isolated environment
        gemini_config_dir = tmp_path / ".gemini"
        gemini_config_dir.mkdir()
        
        # We find the absolute path to the currently running extension
        ext_dir = Path(__file__).parent.parent.parent.absolute()
        
        print(f"Setting up isolated codebase-knowledge MCP server...")
        
        # We use CliRunner to invoke the setup command in-process, patching Path.home()
        # to ensure it modifies the temporary directory, not the user's real home.
        runner = CliRunner()
        
        # Arguments for the setup command
        args = [
            "setup",
            "--repo-url", "https://github.com/google/adk-python.git",
            "--version", "v1.20.0",
            "--force",
            "--local", str(ext_dir),
            "--quiet"
        ]
        
        # Patch Path.home() to return our temp path
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(manage_mcp.cli, args)
            
            if result.exit_code != 0:
                print(f"Setup failed output: {result.output}")
                
            assert result.exit_code == 0, f"Setup failed with code {result.exit_code}"

        # 2. Run the Gemini CLI to trigger the dynamic clone
        # We still shell out to gemini, but we pass HOME so it picks up the config we just wrote.
        env = os.environ.copy()
        env["HOME"] = str(tmp_path)
        
        command_parts = [
            "gemini",
            "--output-format", "json",
            "--model", "gemini-2.5-flash",
            "--yolo", # Auto-approve tool use
            "--debug",
            prompt
        ]
        
        print(f"Executing Gemini CLI to trigger dynamic clone: {' '.join(command_parts)}")
        result = subprocess.run(command_parts, env=env, capture_output=True, text=True)
        
        # 3. Assertions
        assert result.returncode == 0, f"Gemini CLI failed. Stderr: {result.stderr}"
        
        # We loosely check for the tool call in the debug logs (stderr usually)
        assert "read_source_code" in result.stderr, "Extracted read_source_code tool call missing from executing logs"
        
        # Alternatively, parse the final JSON response for the class definition
        response_dict = {}
        try:
            # We look for the last complete JSON object in stdout as the stream output
            # could be messy if multiple prints happen.
            stdout_lines = result.stdout.splitlines()
            for line in reversed(stdout_lines):
                if line.strip().startswith("{"):
                    response_dict = json.loads(line)
                    break
        except Exception:
            pass # Fall back to raw string check

        assert "class BaseAgent" in result.stdout or "class BaseAgent" in result.stderr or "class BaseAgent" in response_dict.get("response", ""), "Could not find 'class BaseAgent' in the output, dynamic clone failed to read the file."
