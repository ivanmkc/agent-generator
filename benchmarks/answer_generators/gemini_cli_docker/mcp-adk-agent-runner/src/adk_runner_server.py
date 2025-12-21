from mcp.server.fastmcp import FastMCP
import importlib.util
import tempfile
import uuid
import sys
import io
import traceback
import os

# Initialize FastMCP server
mcp = FastMCP("adk-agent-runner")

@mcp.tool()
def run_adk_agent(agent_code: str, prompt: str, model_name: str = "gemini-2.5-flash") -> str:
    """
    Executes a Python ADK agent provided as a code string. 
    The code must define a function `create_agent(model_name: str) -> Agent`.
    
    Args:
        agent_code: The complete Python source code defining the agent.
        prompt: The user input or task description to send to the created agent.
        model_name: The model to pass to `create_agent`. Defaults to "gemini-2.5-flash".
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
        
        result = None
        execution_error = None
        
        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # Attempt to run the agent using standard ADK/LangChain interfaces
            if hasattr(agent, "invoke"):
                result = agent.invoke(prompt)
            elif hasattr(agent, "run"):
                result = agent.run(prompt)
            elif callable(agent):
                # Maybe it returned a runnable callable directly?
                result = agent(prompt)
            else:
                return f"Error: Created agent object of type {type(agent)} has no 'invoke', 'run', or '__call__' method."
                
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
