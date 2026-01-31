import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting MCP Verification ---")
    
    settings_path = Path("/root/.gemini/settings.json")
    if not settings_path.exists():
        print(f"FAIL: Settings file not found at {settings_path}")
        sys.exit(1)
        
    try:
        with open(settings_path, "r") as f:
            settings = json.load(f)
    except Exception as e:
        print(f"FAIL: Invalid JSON in settings.json: {e}")
        sys.exit(1)
        
    # We now look for 'codebase-knowledge' or whatever was configured
    server_key = list(settings.get("mcpServers", {}).keys())[0]
    config = settings.get("mcpServers", {}).get(server_key)
    
    print(f"Found server configuration: {server_key}")
    
    cmd = config["command"]
    args = config.get("args", [])
    env = config.get("env", {})
    
    expanded_env = os.environ.copy()
    for k, v in env.items():
        expanded_env[k] = os.path.expandvars(v)
        
    server_params = StdioServerParameters(
        command=cmd,
        args=args,
        env=expanded_env
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Server Initialized.")
                
                tools_result = await session.list_tools()
                tool_names = [t.name for t in tools_result.tools]
                print(f"Available Tools: {tool_names}")
                
                # Generic names
                required_tools = ["list_modules", "inspect_symbol", "read_source_code"]
                if not all(t in tool_names for t in required_tools):
                    print(f"FAIL: Missing tools. Found: {tool_names}")
                    sys.exit(1)

                print("Testing 'list_modules'...")
                result = await session.call_tool("list_modules", arguments={"page": 1})
                content = result.content[0].text
                
                if "Ranked Modules" in content:
                    print("SUCCESS: Index loaded and tools working.")
                else:
                    print(f"FAIL: Unexpected tool output: {content[:200]}...")
                    sys.exit(1)

                print("Testing 'read_source_code' (Triggers Clone)...")
                # Use a known class from the dummy index
                result = await session.call_tool("read_source_code", arguments={"fqn": "google.adk.agents.llm_agent.LlmAgent"})
                content = result.content[0].text
                
                if "class LlmAgent" in content:
                    print("SUCCESS: Source code retrieved.")
                else:
                    print(f"FAIL: Could not read source: {content[:200]}...")
                    sys.exit(1)
                
    except Exception as e:
        print(f"FAIL: Error during MCP communication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
