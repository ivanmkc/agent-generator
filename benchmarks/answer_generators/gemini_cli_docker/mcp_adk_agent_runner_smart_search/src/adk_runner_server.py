from mcp.server.fastmcp import FastMCP
import importlib.util
import tempfile
import uuid
import sys
import io
import traceback
import os
import asyncio
from typing import Any, Optional

# Imports for ADK execution
from google.adk.apps import App
from google.adk.runners import InMemoryRunner
from google.genai import types

# Initialize FastMCP server
mcp = FastMCP("adk-agent-runner")


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
        sys.executable, "-m", "pydoc", module_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        return f"Error getting help for {module_name}:\n{stderr.decode()}"
    return stdout.decode()


@mcp.tool()
async def run_adk_agent(
    agent_code: str,
    prompt: str,
    model_name: str = "gemini-2.5-flash",
    initial_state: Optional[dict[str, Any]] = None,
) -> str:
    """
    Executes a Python ADK agent provided as a code string.
    The code must define a function `create_agent(model_name: str) -> Agent`.

    Args:
        agent_code: The complete Python source code defining the agent.
        prompt: The user input or task description to send to the created agent.
        model_name: The model to pass to `create_agent`. Defaults to "gemini-2.5-flash".
        initial_state: Optional dictionary for initial session state.
    """
    # 1. Persist code to temp file
    module_name = f"dynamic_agent_{uuid.uuid4().hex}"
    # Use a safe temp directory
    tmp_dir = tempfile.gettempdir()
    tmp_file_path = os.path.join(tmp_dir, f"{module_name}.py")

    with open(tmp_file_path, "w", encoding="utf-8") as f:
        f.write(agent_code)

    try:
        # 2. Load module dynamically
        spec = importlib.util.spec_from_file_location(module_name, tmp_file_path)
        if not spec or not spec.loader:
            return f"Error: Could not load spec for {tmp_file_path}"

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 3. Instantiate Agent
        if not hasattr(module, "create_agent"):
            return "Error: The provided code does not define a function `create_agent(model_name: str)`."

        # Call the factory function
        try:
            agent = module.create_agent(model_name=model_name)
        except Exception:
            return f"Error during agent instantiation (create_agent):\n{traceback.format_exc()}"

        # 4. Execute with Stdout/Stderr Capture
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        result = ""
        execution_error = None

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Setup Runner
            # We use a unique app name to avoid collisions if multiple agents are run
            app = App(name=f"runner_app_{uuid.uuid4().hex}", root_agent=agent)
            runner = InMemoryRunner(app=app)

            # Create Session
            session = await runner.session_service.create_session(
                app_name=app.name, user_id="runner-user", state=initial_state or {}
            )

            # Run
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
            ):
                # Simple accumulation of text parts from the agent's response
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            result += part.text
                        # We could also capture function calls here if needed for debugging

        except Exception:
            execution_error = traceback.format_exc()
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        logs = f"--- Logs ---\nStdout:\n{stdout_capture.getvalue()}\nStderr:\n{stderr_capture.getvalue()}"

        if execution_error:
            return f"Agent Execution Failed:\n{execution_error}\n\n{logs}"

        return f"Response: {result}\n\n{logs}"

    except Exception:
        return f"System Error in run_adk_agent:\n{traceback.format_exc()}"
    finally:
        # Cleanup
        if os.path.exists(tmp_file_path):
            try:
                os.remove(tmp_file_path)
            except OSError:
                pass


if __name__ == "__main__":
    mcp.run()
