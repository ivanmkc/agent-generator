import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("--- Starting Bundled Index Verification ---")
    
    server_params = StdioServerParameters(
        command="codebase-knowledge-mcp",
        args=[],
        env={
            "TARGET_REPO_URL": "https://bundled.com/repo.git",
            "TARGET_VERSION": "v1.0.0"
        }
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Server Initialized.")
            
            # Check if list_modules works
            # If bundled index was used, it should return 'bundled.symbol'
            print("Calling list_modules...")
            result = await session.call_tool("list_modules", arguments={"page": 1})
            content = result.content[0].text
            print(f"Tool Output: {content}")
            
            if "bundled.symbol" in content:
                print("SUCCESS: Loaded bundled index correctly.")
            else:
                print(f"FAIL: Did not find expected symbol in output.")
                sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
