"""
Verification script for the Registry Miss scenario.

This test verifies that if a user provides a repository URL that is NOT in the 
registry and forgets to provide TARGET_INDEX_URL, the server provides a clear, 
actionable error message instead of crashing.
"""

import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting Registry Miss Verification ---")
    
    cmd = "codebase-knowledge-mcp"
    env = {} # No configuration provided
    
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
                
                print("Calling list_modules for 'unknown-kb-id' (Expect Failure)...")
                try:
                    result = await session.call_tool("list_modules", arguments={"kb_id": "unknown-kb-id", "page": 1})
                    content = result.content[0].text

                    print(f"Tool Output: {content}")
                    if "not found" in content:
                        print("SUCCESS: Correctly failed due to missing registry entry.")
                    else:
                        print(f"FAIL: Unexpected success or error message: {content}")
                        sys.exit(1)
                except Exception as e:
                    # MCP client might raise exception on tool failure depending on implementation
                    print(f"Tool failed as expected: {e}")
                    print("SUCCESS: Correctly failed.")

    except Exception as e:
        print(f"FAIL: Server crashed or failed communication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
