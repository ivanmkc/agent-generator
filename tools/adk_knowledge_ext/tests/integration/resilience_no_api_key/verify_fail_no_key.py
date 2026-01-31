"""
Verification script for the Missing API Key scenario.

This test ensures that if a user explicitly requests 'hybrid' or 'vector' search 
but fails to provide GEMINI_API_KEY, the server fails fast with a specific 
ValueError to prevent runtime errors during tool usage.
"""

import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting Resilience Verification (Hybrid search, No Key) ---")
    
    cmd = "codebase-knowledge-mcp"
    env = {
        "ADK_SEARCH_PROVIDER": "hybrid",
        "GEMINI_API_KEY": "", # Explicitly empty
        "TARGET_VERSION": "v1.20.0" # Ensure index exists so we trigger the load() logic
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
                
                print("Calling list_modules (Expect failure due to no key)...")
                result = await session.call_tool("list_modules", arguments={"page": 1})
                content = result.content[0].text
                print(f"Tool Output: {content}")
                
                if "API key is required" in content:
                    print("SUCCESS: Server correctly failed tool call due to missing API key.")
                else:
                    print(f"FAIL: Unexpected output: {content}")
                    sys.exit(1)

    except Exception as e:
        print(f"FAIL: Server crashed or failed communication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())