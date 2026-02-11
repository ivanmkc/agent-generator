from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import FunctionTool, exit_loop
from .models import ClaimList

class ClaimAnalystAgent(LlmAgent):
    """
    Analyzes the question and decomposes it into testable claims.
    """
    def __init__(self, model, tools_helper):
        tools = [
            FunctionTool(tools_helper.search_ranked_targets),
            FunctionTool(tools_helper.inspect_fqn),
            FunctionTool(tools_helper.read_file),
            FunctionTool(tools_helper.search_files),
        ]
        
        super().__init__(
            name="claim_analyst",
            model=model,
            tools=tools,
            output_key="claims_json",  # Save output to session state
            output_schema=ClaimList,   # Using Pydantic BaseModel exactly as requested
            instruction=(
                "You are a Senior QA Analyst. Your task is to audit a benchmark question.\n"
                "Input: A Multiple Choice Question with options.\n"
                "Goal: Decompose each option into a specific, testable hypothesis (Claim).\n"
                "\n"
                "Process:\n"
                "1. Research the codebase using `search_ranked_targets` or `inspect_fqn` to understand the relevant classes and methods.\n"
                "   - Verify if the classes/methods mentioned in the question even exist.\n"
                "2. For EACH option (A, B, C, D...), formulate a hypothesis.\n"
                "   - Positive Claim: 'Option A implies code X runs successfully'.\n"
                "   - Negative Claim: 'Option B implies code Y raises ValidationError'.\n"
                "\n"
                "CRITICAL: Do not try to solve the question yet. Just define what needs to be proved.\n"
                "Output must exactly match the required JSON schema structure containing the claim list.\n"
                "CRITICAL: Do NOT attempt to use tools you do not have mapping to like run_programming_task. Only use mapped tools like search_files, read_file."
            )
        )

class ProofEngineerAgent(LlmAgent):
    """
    Writes and executes pytest scripts to prove claims.
    """
    def __init__(self, model, tools_helper):
        tools = [
            FunctionTool(tools_helper.write_file),
            FunctionTool(tools_helper.run_shell_command),
            FunctionTool(tools_helper.read_file),
            FunctionTool(tools_helper.read_full_execution_logs),
            FunctionTool(exit_loop),
        ]
        
        super().__init__(
            name="proof_engineer",
            model=model,
            tools=tools,
            include_contents="default",
            output_key="engineer_log",
            instruction=(
                "You are a Proof Engineer. You have a list of Claims in `session.state.claims_json` (look at previous turns or extract from history).\n"
                "Your goal is to empirically PROVE whether each claim is True or False using `pytest`.\n"
                "\n"
                "Process:\n"
                "1. Pick an unproven claim from the list.\n"
                "2. Write a standalone `pytest` file (e.g., `test_option_A.py`).\n"
                "   - Use `pytest.raises(...)` if you expect an error.\n"
                "   - Use assertions if you expect success.\n"
                "   - IMPORTANT: Mock external calls if necessary. Use `unittest.mock`.\n"
                "3. Execute: `run_shell_command('pytest test_option_A.py', description='Verifying that Option A initializes correctly')`.\n"
                "   - CRITICAL: You MUST provide a natural language `description` in the `run_shell_command` call explaining EXACTLY what this test proves.\n"
                "4. Analyze the result. Did the test PASS (proving the claim) or FAIL?\n"
                "   - Note: If a Negative Claim (expecting error) PASSES, it means the error WAS raised, so the claim is TRUE.\n"
                "5. Repeat until ALL claims are tested.\n"
                "   - CRITICAL: DO NOT DELETE the `pytest` files or any other generated scripts. They must remain in the workspace for archival.\n"
                "6. Once all claims are tested, output a summary of results and call `exit_loop()`."
            )
        )

def build_multiple_choice_pipeline(model, tools_helper) -> list:
    """Builds the agent sequence for MC questions."""
    claim_analyst = ClaimAnalystAgent(model, tools_helper)
    proof_engineer = ProofEngineerAgent(model, tools_helper)
    proof_loop = LoopAgent(
        name="proof_loop",
        sub_agents=[proof_engineer],
        max_iterations=8
    )
    return [claim_analyst, proof_loop]
