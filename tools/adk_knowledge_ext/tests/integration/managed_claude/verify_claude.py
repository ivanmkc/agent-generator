"""
Verification script for Claude Code Setup.

Verifies that the management tool uses the correct CLI structure for Claude Code:
claude mcp add --scope user codebase-knowledge -- env ...
(Notice the -- separator BEFORE the command)
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("--- Starting Claude Code Managed Setup Verification ---")
    
    log_file = Path("/tmp/claude_log")
    if log_file.exists():
        log_file.unlink()
        
    # Mock Claude detection
    Path.home().joinpath(".claude").mkdir(exist_ok=True)
    
    # 1. Setup
    print("Running setup...")
    cmd = [
        "codebase-knowledge-mcp-manage", "setup",
        "--repo-url", "https://github.com/test/repo.git",
        "--version", "v1.0.0",
        "--force"
    ]
    subprocess.run(cmd, check=True)
    
    # Verify log
    with open(log_file, "r") as f:
        log = f.read()
    
    print(f"Claude Mock Log:\n{log}")
    
    # Claude uses: mcp add name -- env ...
    if "claude mcp add --scope user codebase-knowledge -- env" in log:
        print("SUCCESS: Claude setup uses correct separator style.")
    else:
        print("FAIL: Claude setup CLI structure mismatch.")
        sys.exit(1)

    # 2. Remove
    print("Running remove...")
    subprocess.run(["codebase-knowledge-mcp-manage", "remove"], input="y\ny\n", text=True)
    
    # Verify removal call
    with open(log_file, "r") as f:
        log = f.read()
    
    if "claude mcp remove codebase-knowledge --scope user" in log:
        print("SUCCESS: Claude remove called correctly.")
    else:
        print("FAIL: Claude remove call missing.")
        sys.exit(1)

if __name__ == "__main__":
    main()
