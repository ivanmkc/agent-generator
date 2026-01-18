from mcp.server.fastmcp import FastMCP
from adk_agent_tool import run_adk_agent

# Initialize FastMCP server
mcp = FastMCP("adk-agent-runner")

# Register the shared tool
mcp.tool()(run_adk_agent)

if __name__ == "__main__":
    mcp.run()