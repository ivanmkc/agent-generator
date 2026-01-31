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

    # 4. Test --knowledge-index-url (Re-setup)
    print("Step 5: Re-running setup with --knowledge-index-url (local file)...")
    
    # Create dummy index
    dummy_index = Path("/tmp/test_index.yaml")
    dummy_index.write_text("- name: test.module\n  type: MODULE\n  rank: 1")
    index_url = f"file://{dummy_index}"

    cmd_k_index = [
        "codebase-knowledge-mcp-manage", "setup",
        "--repo-url", "https://github.com/test/repo.git",
        "--version", "v1.0.0",
        "--api-key", "fake-key",
        "--knowledge-index-url", index_url,
        "--force"
    ]
    run_command(cmd_k_index)
    
    print("Step 6: Verifying TARGET_INDEX_URL in config...")
    result = subprocess.run(list_cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    print(f"Gemini Output:\n{output}")
    
    if f"TARGET_INDEX_URL={index_url}" in output:
        print("SUCCESS: TARGET_INDEX_URL found in configuration.")
    else:
        print("FAIL: TARGET_INDEX_URL missing from configuration.")
        sys.exit(1)

    # 5. Verify Tool Execution
    print("Step 7: Verifying Tool Execution...")
    import json
    settings_path = Path.home() / ".gemini" / "settings.json"
    if not settings_path.exists():
        print(f"FAIL: Settings file not found at {settings_path}")
        sys.exit(1)
        
    try:
        settings = json.loads(settings_path.read_text())
        server_config = settings.get("mcpServers", {}).get("codebase-knowledge")
        if not server_config:
            print("FAIL: Server config not found in JSON.")
            sys.exit(1)
            
        full_cmd = [server_config["command"]] + server_config.get("args", [])
        
        # TEST FIX: In the test container, 'uvx' fails to clone from GitHub due to env/auth.
        # However, we have already installed the package locally via pip in the Dockerfile.
        # We override the command to run the locally installed server directly, 
        # ensuring we verify the *logic* and *config* (env vars) without network dependencies.
        if full_cmd[0] == "uvx":
            print("Test Override: Replacing 'uvx' with local 'codebase-knowledge-mcp' binary.")
            full_cmd = ["codebase-knowledge-mcp"]

        env = os.environ.copy()
        env.update(server_config.get("env", {}))
        
        print(f"Launching Server: {' '.join(full_cmd)}")
        
        # Start Server
        proc = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            env=env,
            text=True,
            bufsize=0
        )
        
        # Send Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()
        
        # Read Initialize Response
        resp_line = proc.stdout.readline()
        print(f"Init Response: {resp_line}")
        if "result" not in resp_line:
             print("FAIL: Initialization failed.")
             sys.exit(1)

        # Send Initialized Notification
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

        # Send Tool Call
        tool_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "list_modules",
                "arguments": {}
            }
        }
        proc.stdin.write(json.dumps(tool_req) + "\n")
        proc.stdin.flush()
        
        # Read Tool Response
        tool_resp_line = proc.stdout.readline()
        print(f"Tool Response: {tool_resp_line}")
        
        if "test.module" in tool_resp_line:
            print("SUCCESS: Tool execution verified (index loaded).")
        else:
            print(f"FAIL: Expected 'test.module' in response, got: {tool_resp_line}")
            sys.exit(1)
            
        proc.terminate()
        
    except Exception as e:
        print(f"FAIL: Execution error: {e}")
        sys.exit(1)

    # 6. Remove
    print("Step 8: Running remove...")
    cmd_remove = ["codebase-knowledge-mcp-manage", "remove"]
    
    # Pipe 'y' for confirmation
    p = subprocess.Popen(cmd_remove, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(input="y\n")
    
    if p.returncode != 0:
        print(f"Remove failed: {stderr}")
        sys.exit(1)

    # 7. Verify Removal
    print("Step 9: Verifying removal...")
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