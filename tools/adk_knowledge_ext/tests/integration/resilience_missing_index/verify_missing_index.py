import json
import os
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting Resilience Verification (Valid Version, Missing Index) ---")
    
    # FIX: Use correct generic command name
    cmd = "codebase-knowledge-mcp"
    env = {
        "TARGET_VERSION": "v1.20.0",
    }
    
    server_params = StdioServerParameters(
        command=cmd,
        args=[],
        env=env
    )
    
    print(f"Launching Server...")
    
    failure = False
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Server Initialized.")
                
                # 1. Test Index (Should be missing)
                print("Calling list_modules for 'unknown-kb' (Expect helpful rejection)...")
                result = await session.call_tool("list_modules", arguments={"kb_id": "unknown-kb", "page": 1})
                content = result.content[0].text
                print(f"Tool Output: {content}")
                
                if "not found" in content or "not supported" in content:
                    print("SUCCESS: Handled missing index gracefully.")
                else:
                    print(f"FAIL: Unexpected output: {content}")
                    failure = True


                # 2. Test Symbol retrieval
                print("Calling read_source_code (Expect failure due to no index)...")
                result = await session.call_tool("read_source_code", arguments={"fqn": "google.adk.agents.llm_agent.LlmAgent"})
                content = result.content[0].text
                print(f"Tool Output: {content}")
                
                if "not supported" in content or "no index" in content or "not properly set up" in content:
                    print("SUCCESS: Correctly reported failure (due to missing index).")
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