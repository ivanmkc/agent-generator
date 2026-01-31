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
    
    # Expand env vars
    expanded_env = os.environ.copy()
    for k, v in env.items():
        expanded_env[k] = os.path.expandvars(v)
        
    server_params = StdioServerParameters(
        command=cmd,
        args=args,
        env=expanded_env
    )
    
    # 4. Connect and Verify
    print(f"Launching Server: {cmd} {args}")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Server Initialized.")
                
                # Check Tools
                tools_result = await session.list_tools()
                tool_names = [t.name for t in tools_result.tools]
                print(f"Available Tools: {tool_names}")
                
                required_tools = ["list_adk_modules", "inspect_adk_symbol"]
                if not all(t in tool_names for t in required_tools):
                    print(f"FAIL: Missing tools. Found: {tool_names}")
                    sys.exit(1)

                # Functional Test: List Modules
                # This confirms the index loaded correctly
                print("Testing 'list_adk_modules'...")
                result = await session.call_tool("list_adk_modules", arguments={"page": 1})
                content = result.content[0].text
                
                if "--- Ranked Targets" in content:
                    print("SUCCESS: Index loaded and tools working.")
                else:
                    print(f"FAIL: Unexpected tool output: {content[:200]}...")
                    sys.exit(1)

                # Functional Test: Source Reading (Triggers Cloning)
                print("Testing 'read_adk_source_code' (Triggers Clone)...")
                # Use a known class from the index
                result = await session.call_tool("read_adk_source_code", arguments={"fqn": "google.adk.agents.llm_agent.LlmAgent"})
                content = result.content[0].text
                
                if "class LlmAgent" in content:
                    print("SUCCESS: Source code retrieved (Clone successful).")
                else:
                    print(f"FAIL: Could not read source: {content[:200]}...")
                    sys.exit(1)
                
    except Exception as e:
        print(f"FAIL: Error during MCP communication: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())