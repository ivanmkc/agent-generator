import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

def run_cmd(cmd, cwd=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout

async def verify_tool_execution(server_config):
    print("--- Verifying Tool Execution ---")
    cmd = server_config['command']
    args = server_config['args']
    # Parse env from args if command is 'env'
    env = os.environ.copy()
    
    if cmd == 'env':
        actual_args = []
        for arg in args:
            if '=' in arg and not arg.startswith('-') and 'uvx' not in arg:
                 k, v = arg.split('=', 1)
                 env[k] = v
            else:
                actual_args.append(arg)
        # The command is the first actual arg
        executable = actual_args[0]
        final_args = actual_args[1:]
    else:
        executable = cmd
        final_args = args
        env.update(server_config.get('env', {}))

    print(f"Executable: {executable}")
    print(f"Args: {final_args}")
    print(f"Repo URL in Env: {env.get('TARGET_REPO_URL')}")

    server_params = StdioServerParameters(
        command=executable,
        args=final_args,
        env=env
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("MCP Initialized.")
            
            # Call 'list_modules'
            result = await session.call_tool("list_modules", arguments={"page": 1})
            content = result.content[0].text
            # print(content[:200])
            
            if "Ranked Modules" in content:
                print("SUCCESS: Tool executed successfully.")
            else:
                raise RuntimeError(f"Tool output unexpected: {content}")

def main():
    try:
        src_dir = "/src/tools/adk_knowledge_ext"
        
        # 1. Setup
        print("\n=== Step 1: Setup ===")
        # We use --local to point to the source directory
        setup_cmd = [
            "uvx", "--from", src_dir,
            "codebase-knowledge-mcp-manage", "setup",
            "--repo-url", "https://github.com/google/adk-python.git",
            "--version", "v1.20.0",
            "--local",
            "--force"
        ]
        # We must run this from src_dir so the relative path logic works or just pass absolute path (which we did)
        # Wait, if --local is passed, manage_mcp tries to resolve current dir.
        # So we should run it FROM src_dir.
        run_cmd(setup_cmd, cwd=src_dir)

        # 2. Verify Config
        print("\n=== Step 2: Verify Config ===")
        config_path = Path.home() / ".gemini" / "settings.json"
        if not config_path.exists():
            raise RuntimeError("Config file not generated.")
        
        with open(config_path) as f:
            gemini_config = json.load(f)
            
        mcp_config = gemini_config['mcpServers']['codebase-knowledge']
        print(json.dumps(mcp_config, indent=2))
        
        # Check if index URL was resolved (it should be, via registry lookup in manage_mcp)
        # Note: manage_mcp puts it in args/env
        args_str = str(mcp_config['args'])
        if "TARGET_INDEX_URL" not in args_str:
            print("WARNING: TARGET_INDEX_URL not found in config. Ensure registry lookup worked.")
        else:
            print("Config contains TARGET_INDEX_URL.")

        # 3. Verify Tool Execution (Async)
        print("\n=== Step 3: Tool Verification ===")
        # This will trigger the actual server execution.
        # If bundling worked, the server will find the index locally (bundled)
        # OR it will download it using TARGET_INDEX_URL (if provided).
        # Since we patched registry.yaml, bundling SHOULD have happened.
        # AND manage_mcp should have provided the URL.
        # The server prioritizes Bundled Manifest.
        asyncio.run(verify_tool_execution(mcp_config))

        # 4. Remove
        print("\n=== Step 4: Remove ===")
        # We pipe 'y' to confirm removal
        remove_cmd = ["uvx", "--from", src_dir, "codebase-knowledge-mcp-manage", "remove"]
        p = subprocess.Popen(remove_cmd, cwd=src_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = p.communicate(input="y\n")
        if p.returncode != 0:
            raise RuntimeError(f"Remove failed: {stderr}")
        print("Removal command executed.")

        # 5. Verify Removal
        print("\n=== Step 5: Verify Removal ===")
        with open(config_path) as f:
            gemini_config = json.load(f)
        
        if "codebase-knowledge" in gemini_config.get("mcpServers", {}):
            raise RuntimeError("Server config still present after removal.")
        
        print("SUCCESS: Server removed.")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
