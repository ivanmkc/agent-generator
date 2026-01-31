import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting Resilience Verification (Invalid Version) ---")
    
    # Minimal config setup for testing
    cmd = "adk-knowledge-mcp"
    env = {
        "ADK_VERSION": "v9.9.9", # Non-existent version
    }
    
    server_params = StdioServerParameters(
        command=cmd,
        args=[],
        env=env
    )
    
    print(f"Launching Server with invalid version...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Server Initialized (Survived startup).")
                
                # Test Tool Behavior
                print("Calling list_adk_modules...")
                result = await session.call_tool("list_adk_modules", arguments={"page": 1})
                content = result.content[0].text
                
                print(f"Tool Output: {content}")
                
                if "No items found" in content:
                    print("SUCCESS: Server handled missing index gracefully.")
                else:
                    print(f"FAIL: Unexpected output: {content}")
                    sys.exit(1)

    except Exception as e:
        print(f"FAIL: Server crashed or failed communication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())