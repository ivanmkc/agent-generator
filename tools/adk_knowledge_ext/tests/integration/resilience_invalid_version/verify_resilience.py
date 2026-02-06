import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting Resilience Verification (Invalid Version) ---")
    
    cmd = "codebase-knowledge-mcp"
    env = {
        "TARGET_REPO_URL": "https://github.com/google/adk-python.git",
        "TARGET_VERSION": "v9.9.9", 
    }
    
    server_params = StdioServerParameters(
        command=cmd,
        args=[],
        env=env
    )
    
    try:
        failure = False
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Server Initialized.")
                
                print("Calling list_modules...")
                result = await session.call_tool("list_modules", arguments={"page": 1})
                content = result.content[0].text

                
                if "not supported" in content or "not found" in content or "No Knowledge Bases" in content:
                    print("SUCCESS: Server handled invalid version/missing index gracefully.")
                else:
                    print(f"FAIL: Unexpected output: {content}")
                    failure = True
                    
    except Exception as e:
        print(f"FAIL: Server crashed or failed communication: {e}")
        failure = True

    if failure:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())