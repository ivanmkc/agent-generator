"""
Verification script for Managed Setup (CLI Integration).

Tests the `codebase-knowledge-mcp-manage` CLI tool's ability to detect and 
configure the 'Gemini CLI' tool by invoking the underlying `mcp` command.
It mocks the `gemini` executable to verify arguments.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("--- Starting Managed Setup Verification ---")
    
    # 1. Setup
    print("Running setup...")
    cmd = [
        "codebase-knowledge-mcp-manage", "setup",
        "--repo-url", "https://github.com/test/repo.git",
        "--version", "v1.0.0",
        "--api-key", "fake-key",
        "--force"
    ]
    
    # We need to simulate the 'gemini' config path existence so the tool detects it
    # manage_mcp.py checks: Path.home() / ".gemini"
    gemini_home = Path.home() / ".gemini"
    gemini_home.mkdir(parents=True, exist_ok=True)
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Setup failed: {e}")
        sys.exit(1)
        
    # Verify Mock Log
    log_path = Path("/tmp/gemini_mock.log")
    if not log_path.exists():
        print("FAIL: Mock gemini CLI was not called.")
        sys.exit(1)
        
    log_content = log_path.read_text()
    print(f"Mock Log:\n{log_content}")
    
    # Check if 'gemini mcp add' was called with correct args
    # Expected: gemini mcp add user codebase-knowledge env -- TARGET_REPO_URL=... uvx ...
    if "mcp add --scope user codebase-knowledge" in log_content and "uvx" in log_content:
        print("SUCCESS: Setup called gemini correctly.")
    else:
        print("FAIL: Setup command mismatch.")
        sys.exit(1)

    # 2. Remove
    print("Running remove...")
    cmd_remove = ["codebase-knowledge-mcp-manage", "remove"]
    # Force confirmation (manage_mcp.py uses Confirm.ask which reads stdin)
    # We need to pipe 'y' to it.
    
    p = subprocess.Popen(cmd_remove, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(input="y\n")
    
    if p.returncode != 0:
        print(f"Remove failed: {stderr}")
        sys.exit(1)
        
    log_content = log_path.read_text()
    print(f"Mock Log (Updated):\n{log_content}")
    
    if "mcp remove codebase-knowledge --scope user" in log_content:
        print("SUCCESS: Remove called gemini correctly.")
    else:
        print("FAIL: Remove command mismatch.")
        sys.exit(1)

if __name__ == "__main__":
    main()
