#!/usr/bin/env python3
import sys
import os

SIMULATOR_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, SIMULATOR_ROOT)

from simulator import SimulationRunner
from models import (
    InteractiveSimulationCase,
    LLMReactor,
    ActionType,
    ReactorAction,
    FileExpectation
)

AGENT_PERSONAS = [
    {
        "name": "Universal Fact Checker",
        "description": "An L2 adk-python agent that uses a search tool to verify claims and appends citations."
    },
    {
        "name": "Polyglot Translator",
        "description": "An L1 adk-python agent heavily prompted to retain idiomatic structures when translating between programming languages."
    },
    {
        "name": "Sentiment Analyst",
        "description": "An L1 adk-python agent that processes customer reviews and returns strictly typed JSON sentiment scores."
    },
    {
        "name": "Code Explainer",
        "description": "An L1 adk-python agent designed to analyze complex code snippets and return a Markdown summary of its time/space complexity."
    },
    {
        "name": "Prompt Optimizer",
        "description": "An L2 adk-python agent that rewrites user prompts to be more effective for LLMs."
    },
    {
        "name": "Documentation Generator",
        "description": "An L3 adk-python agent that reads a codebase and writes detailed MD documentation files."
    },
    {
        "name": "SQL Query Assistant",
        "description": "An L3 adk-python agent that translates natural language into optimized postgres SQL queries."
    },
    {
        "name": "GitHub Issue Summarizer",
        "description": "An L4 adk-python agent acting sequentially to fetch issues and generate a weekly triage report."
    },
    {
        "name": "Release Note Bot",
        "description": "An L4 adk-python sequential agent that pulls package.json versions and parses git logs to write structured release notes."
    },
    {
        "name": "Unit Test Crafter",
        "description": "An L4 adk-python agent that generates pytest cases for provided functions, runs the tests via a subprocess tool, and fixes the tests if they fail."
    }
]

def generate_agents():
    # Make a directory to hold the generated agents
    output_dir = os.path.abspath(os.path.join(SIMULATOR_ROOT, "..", "generated_agents"))
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Starting mass generation of {len(AGENT_PERSONAS)} agents in {output_dir}\n")

    for i, persona in enumerate(AGENT_PERSONAS):
        idx = i + 1
        print(f"--- GENERATING AGENT {idx}/10: {persona['name']} ---")
        
        filename = f"{persona['name'].lower().replace(' ', '_')}.py"
        
        # We explicitly instruct the agent to write the code, RUN IT, and fix exceptions.
        prompt = f"""You are an elite Python developer perfectly familiar with the `google-adk` ('adk-python') framework.
Please write `{filename}` which implements the following:
{persona['description']}

CRITICAL REQUIREMENT:
1. You MUST write the complete python code to `{filename}`.
2. You MUST execute `python {filename}` to test it locally. (Include a standard `if __name__ == "__main__":` block with a trivial test case).
3. If the script throws any errors, you MUST read the stack trace and fix `{filename}`.
4. ONLY stop once the script executes flawlessly with no errors. Do not stop before executing it yourself.
"""

        case = InteractiveSimulationCase(
            name=f"Generate {persona['name']}",
            initial_prompt=prompt,
            reactors=[
                LLMReactor(
                    goal_prompt=(
                        "The agent has successfully written the requested agent python script, "
                        "actually executed it locally via terminal commands, saw a successful exit code (no traceback), "
                        "and stated that it is finished."
                    ),
                    action=ReactorAction(type=ActionType.END_TEST, payload="Agent successfully written, executed, and verified.")
                ),
                LLMReactor(
                    goal_prompt="The agent ran the script but it failed, or the agent is asking if they should run it.",
                    action=ReactorAction(type=ActionType.RESPOND, payload="Please run the script and fix any errors until it exits cleanly.")
                )
            ],
            expected_files=[
                FileExpectation(path=filename, exists=True, contains_text="adk")
            ],
            max_turns=15
        )
        
        # We run the simulation. If success, we copy the generated file out from the simulator's tmp_dir.
        # We can leverage custom_verify to extract the file.
        def extract_generated_file(tmp_dir, harness):
            src = os.path.join(tmp_dir, filename)
            dst = os.path.join(output_dir, filename)
            if os.path.exists(src):
                import shutil
                shutil.copy2(src, dst)
                print(f"Extracted {filename} to {output_dir}")
                return True
            return False
            
        case.custom_verify = extract_generated_file
        
        success = SimulationRunner.run(case)
        if not success:
            print(f"WARNING: Generation failed for {persona['name']}.")
            
    print("\n--- Agent Generation Complete ---")

if __name__ == "__main__":
    generate_agents()
