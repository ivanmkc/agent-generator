import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting Resilience Verification (Valid Version, Missing Index) ---")
    
    cmd = "adk-knowledge-mcp"
    # Use valid version so cloning works, but we deleted the index file
    env = {
        "ADK_VERSION": "v1.20.0",
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
                
                # 1. Test Index (Should be empty/missing)
                print("Calling list_adk_modules (Expect empty)...")
                result = await session.call_tool("list_adk_modules", arguments={"page": 1})
                content = result.content[0].text
                print(f"Tool Output: {content}")
                
                if "No items found" in content:
                    print("SUCCESS: Handled missing index gracefully.")
                else:
                    print(f"FAIL: Unexpected output: {content}")
                    sys.exit(1)

                # 2. Test Cloning (Should work because version is valid)
                # We need to target a symbol. Without an index, 'resolve_target' might fail 
                # if it relies purely on the map.
                # Let's check server.py 'resolve_target'.
                # It uses get_index().resolve_target(fqn).
                # If index is empty, resolve_target returns (None, fqn).
                # server.py says:
                # if not target: return "Symbol '{fqn}' not found in index."
                # 
                # Wait, if resolve_target returns None, read_adk_source_code returns error.
                # 
                # So if index is missing, we CANNOT use read_adk_source_code because we don't know the file path!
                # The index maps FQN -> File Path.
                # 
                # So verify_missing_index should confirm that read_adk_source_code fails gracefully saying "not found in index".
                
                print("Calling read_adk_source_code (Expect failure due to no index)...")
                result = await session.call_tool("read_adk_source_code", arguments={"fqn": "google.adk.agents.llm_agent.LlmAgent"})
                content = result.content[0].text
                print(f"Tool Output: {content}")
                
                if "not found in index" in content:
                    print("SUCCESS: Correctly reported missing symbol (due to missing index).")
                else:
                    print(f"FAIL: Unexpected output: {content}")
                    sys.exit(1)

    except Exception as e:
        print(f"FAIL: Server crashed or failed communication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
