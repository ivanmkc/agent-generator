import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting MCP Verification ---")
    
    # 1. Locate Settings
    settings_path = Path("/root/.gemini/settings.json")
    if not settings_path.exists():
        print(f"FAIL: Settings file not found at {settings_path}")
        sys.exit(1)
        
    print(f"Found settings at {settings_path}")
    
    # 2. Parse Settings
    try:
        with open(settings_path, "r") as f:
            settings = json.load(f)
    except Exception as e:
        print(f"FAIL: Invalid JSON in settings.json: {e}")
        sys.exit(1)
        
    config = settings.get("mcpServers", {}).get("adk-knowledge")
    if not config:
        print("FAIL: 'adk-knowledge' server config not found in mcpServers.")
        sys.exit(1)
        
    print("Found 'adk-knowledge' configuration.")
    
    # 3. Prepare Server Parameters
    cmd = config["command"]
    args = config.get("args", [])
    env = config.get("env", {})
    
    # Expand env vars in environment definition
    expanded_env = os.environ.copy()
    for k, v in env.items():
        expanded_env[k] = os.path.expandvars(v)
        
    # Check if data paths exist (Sanity check)
    idx_path = expanded_env.get("ADK_INDEX_PATH")
    repo_path = expanded_env.get("ADK_REPO_PATH")
    
    print(f"Checking Data Paths:\n  Index: {idx_path}\n  Repo:  {repo_path}")
    
    if not idx_path or not Path(idx_path).exists():
        print(f"FAIL: Index path does not exist: {idx_path}")
        sys.exit(1)
    # Repo path might just need to be a directory
    if not repo_path or not Path(repo_path).exists():
        print(f"FAIL: Repo path does not exist: {repo_path}")
        sys.exit(1)
        
    server_params = StdioServerParameters(
        command=cmd,
        args=args,
        env=expanded_env
    )
    
    # 4. Connect and List Tools
    print(f"Launching Server: {cmd} {args}")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("Server Initialized.")
                
                tools_result = await session.list_tools()
                tool_names = [t.name for t in tools_result.tools]
                
                print(f"Available Tools: {tool_names}")
                
                required_tools = [
                    "list_adk_modules",
                    "inspect_adk_symbol",
                    "read_adk_source_code",
                    "search_adk_knowledge"
                ]
                
                missing = [t for t in required_tools if t not in tool_names]
                
                if missing:
                    print(f"FAIL: Missing required tools: {missing}")
                    sys.exit(1)
                    
                print("SUCCESS: All required tools found.")
                
    except Exception as e:
        print(f"FAIL: Error during MCP communication: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
