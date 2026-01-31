"""
Verification script for the Registry Lookup scenario.

This test ensures that when TARGET_INDEX_URL is omitted, the server correctly 
identifies the repository URL and version in its internal `registry.yaml` and 
automatically downloads the correct index file.
"""

import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting Registry Lookup Verification ---")
    
    cmd = "codebase-knowledge-mcp"
    # TARGET_REPO_URL matches registry.yaml
    # TARGET_INDEX_URL is OMITTED
    env = {
        "TARGET_REPO_URL": "https://github.com/google/adk-python.git",
        "TARGET_VERSION": "v1.20.0"
    }
    
    server_params = StdioServerParameters(
        command=cmd,
        args=[],
        env=env
    )
    
    print(f"Launching Server...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Server Initialized.")
                
                print("Calling list_modules (Expect Success via Registry)...")
                result = await session.call_tool("list_modules", arguments={"page": 1})
                content = result.content[0].text
                print(f"Tool Output: {content[:100]}...")
                
                if "Ranked Modules" in content:
                    print("SUCCESS: Registry lookup worked.")
                else:
                    print(f"FAIL: Unexpected output: {content}")
                    sys.exit(1)

    except Exception as e:
        print(f"FAIL: Server crashed or failed communication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
