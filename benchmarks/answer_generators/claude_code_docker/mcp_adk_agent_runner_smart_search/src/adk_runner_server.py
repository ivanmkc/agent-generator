"""Adk Runner Server module."""

from mcp.server.fastmcp import FastMCP
from adk_agent_tool import run_adk_agent
import asyncio
import sys

# Initialize FastMCP server
mcp = FastMCP("adk-agent-runner")

# Register the shared tool
mcp.tool()(run_adk_agent)


@mcp.tool()
async def get_module_help(module_name: str) -> str:
    """
    Retrieves the documentation (pydoc) for a Python module.
    Useful for discovering API details without reading source code.
    """
    if not module_name.replace(".", "").replace("_", "").isalnum():
        return "Error: Invalid module name."

    # We can use subprocess to call pydoc
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pydoc",
        module_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        return f"Error getting help for {module_name}:\n{stderr.decode()}"
    return stdout.decode()


if __name__ == "__main__":
    mcp.run()
