"""
Verification script for Managed Setup (CLI Integration).

Tests the `codebase-knowledge-mcp-manage` CLI tool's ability to detect and 
configure the *real* 'Gemini CLI' tool.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd):
    print(f"Running: ", ' '.join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {result.stderr}")
        sys.exit(1)
    return result.stdout

def main():
    print("---" + " Starting Real Managed Setup Verification ---")
    
    # 1. Setup
    print("Step 1: Running setup...")
    cmd = [
        "codebase-knowledge-mcp-manage", "setup",
        "--repo-url", "https://github.com/test/repo.git",
        "--version", "v1.0.0",
        "--api-key", "fake-key",
        "--force"
    ]
    
    # Ensure .gemini directory exists (though CLI might create it)
    Path.home().joinpath(".gemini").mkdir(exist_ok=True)
    
    run_command(cmd)

    # 2. Verify with Gemini CLI
    print("Step 2: Verifying with 'gemini mcp list'...")
    # Note: gemini-cli often prints list to stderr or stdout depending on version.
    # We'll check combined output.
    list_cmd = ["gemini", "mcp", "list"]
    result = subprocess.run(list_cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    print(f"Gemini Output:\n{output}")
    
    if "codebase-knowledge" in output:
        print("SUCCESS: Server found in Gemini config.")
    else:
        print("FAIL: Server not found in Gemini config.")
        sys.exit(1)

    # 3. Test --index-url (Re-setup)
    print("Step 3: Re-running setup with --index-url...")
    cmd_index = [
        "codebase-knowledge-mcp-manage", "setup",
        "--repo-url", "https://github.com/test/repo.git",
        "--version", "v1.0.0",
        "--api-key", "fake-key",
        "--index-url", "https://test.pypi.org/simple",
        "--force"
    ]
    run_command(cmd_index)
    
    print("Step 4: Verifying --index-url in config...")
    result = subprocess.run(list_cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    print(f"Gemini Output:\n{output}")
    
    if "--index-url https://test.pypi.org/simple" in output:
        print("SUCCESS: --index-url found in configuration.")
    else:
        print("FAIL: --index-url missing from configuration.")
        sys.exit(1)

    # 4. Remove
    print("Step 5: Running remove...")
    cmd_remove = ["codebase-knowledge-mcp-manage", "remove"]
    
    # Pipe 'y' for confirmation
    p = subprocess.Popen(cmd_remove, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(input="y\n")
    
    if p.returncode != 0:
        print(f"Remove failed: {stderr}")
        sys.exit(1)

    # 5. Verify Removal
    print("Step 6: Verifying removal...")
    result = subprocess.run(list_cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    print(f"Gemini Output:\n{output}")
    
    if "codebase-knowledge" not in output:
        print("SUCCESS: Server correctly removed.")
    else:
        print("FAIL: Server still present.")
        sys.exit(1)

if __name__ == "__main__":
    main()