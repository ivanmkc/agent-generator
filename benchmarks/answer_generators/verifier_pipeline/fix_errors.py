from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field

from .models import VerificationVerdict

class PatchApplierAgent(LlmAgent):
    """
    Applies the benchmark's gold implementation block into the testing workspace.
    """
    def __init__(self, model, tools_helper):
        tools = [
            FunctionTool(tools_helper.read_file),
            FunctionTool(tools_helper.write_file),
            FunctionTool(tools_helper.search_files),
        ]
        
        super().__init__(
            name="patch_applier",
            model=model,
            tools=tools,
            instruction=(
                "You are an Integration Engineer. You are given a prompt representing a coding challenge and the 'expected_answer' containing the gold implementation.\n"
                "Your objective is to apply the expected answer to the sandbox workspace so that it solves the prompt.\n"
                "\n"
                "Process:\n"
                "1. Read the provided prompt to understand the context.\n"
                "2. The setup context files provided by the benchmark definition have already been copied to the workspace.\n"
                "3. Apply the 'expected_answer' snippet to the relevant files using `write_file` or by rewriting classes.\n"
                "\n"
                "DO NOT attempt to run tests yet. Ensure the syntax is correct and strictly adheres to the provided `expected_answer`."
            )
        )

class ValidationExecutionAgent(LlmAgent):
    """
    Executes validation scripts against the patched environment to determine if the prompt requirements were fulfilled.
    """
    def __init__(self, model, tools_helper):
        tools = [
            FunctionTool(tools_helper.write_file),
            FunctionTool(tools_helper.run_shell_command),
            FunctionTool(tools_helper.read_file),
            FunctionTool(tools_helper.read_full_execution_logs),
        ]
        
        super().__init__(
            name="validation_executor",
            model=model,
            tools=tools,
            instruction=(
                "You are a Verification Tester. You are testing if the code patch applied earlier correctly solves the Prompt.\n"
                "\n"
                "Process:\n"
                "1. The workspace may contain a `validation_test.py` script provided by the benchmark. If so, execute it via `pytest validation_test.py`.\n"
                "2. If no validation script exists, WRITE a new `pytest` script that empirically verifies the requirements specified in the Prompt are fulfilled.\n"
                "3. Execute your tests using `run_shell_command`.\n"
                "4. Carefully examine standard error, standard output, and exit codes of the tests.\n"
                "5. Stop processing once all tests pass or fail."
            )
        )

def build_fix_errors_pipeline(model, tools_helper) -> list:
    """Builds the agent sequence for coding implementation challenges."""
    patch_applier = PatchApplierAgent(model, tools_helper)
    validation_executor = ValidationExecutionAgent(model, tools_helper)
    
    return [patch_applier, validation_executor]
