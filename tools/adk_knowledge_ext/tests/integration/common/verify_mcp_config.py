import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting MCP Verification ---")
    
    settings_path = Path.home() / ".gemini/settings.json"
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
    
    # Handle 'env' command wrapper (used by CLI integrations like Gemini/Claude)
    if cmd == "env":
        new_args = []
        for arg in args:
            if "=" in arg and not arg.startswith("-"): # VAR=VAL
                k, v = arg.split("=", 1)
                env[k] = v
            else:
                new_args.append(arg)
        
        if new_args:
            cmd = new_args[0]
            args = new_args[1:]
            
    print(f"DEBUG: Resolved command '{cmd}'. TEST_LOCAL_OVERRIDE={os.environ.get('TEST_LOCAL_OVERRIDE')}")
    
    # TEST OVERRIDE: If we are running in a test container where 'uvx' might fail 
    # (e.g. git clone auth), but we know the package is installed locally, 
    # we override the command to run the local binary.
    if cmd == "uvx" and os.environ.get("TEST_LOCAL_OVERRIDE"):
        print("Test Override: Replacing 'uvx' with local 'codebase-knowledge-mcp' binary.")
        # We ignore the 'args' (like --from git+...) because the local binary 
        # is already installed and doesn't need them.
        cmd = "codebase-knowledge-mcp"
        args = []

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

                print("Testing 'list_modules' (using default KB)...")
                # We rely on the server's smart defaulting (it picks the active env var repo)
                result = await session.call_tool("list_modules", arguments={"page": 1})
                content = result.content[0].text
                
                if "Ranked Modules" in content:
                    print(f"SUCCESS: Index loaded and tools working. Output:\n{content[:150]}...")
                else:
                    print(f"FAIL: Unexpected tool output: {content[:200]}...")
                    sys.exit(1)

                if os.environ.get("TEST_SKIP_CLONE_CHECK"):
                    print("Skipping 'read_source_code' check (TEST_SKIP_CLONE_CHECK is set).")
                    return

                print("Testing 'read_source_code' (Triggers Clone)...")
                # Use a known class from the dummy index. 
                # Note: 'read_source_code' also supports smart defaulting if kb_id is omitted.
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
