
"""
Integration test module for the 'Ultimate' scenario.
"""
import sys, os
import json
SIMULATOR_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, SIMULATOR_ROOT)

from simulator import SimulationRunner
from models import (
    InteractiveSimulationCase,
    LLMReactor,
    ActionType,
    ReactorAction
)

def test_scenario(backend, output_dir) -> None:
    # 1. Setup 'settings.json' to enable Memory MCP using `uvx`
    #    (simulated by writing to .fake_home/.gemini/settings.json via setup_files)
    
    # We need to construct the settings file content ensuring 'uvx' is used
    settings_content = {
        "mcpServers": {
            "memory": {
                "command": "uvx",
                "args": ["mcp-server-memory"],
                "env": {}
            }
        },
        "tools": {
            "allowed": ["*"] # Allow all tools for this test
        }
    }
    
    # Map it to where the simulator expects it relative to tmp_dir
    # The simulator puts 'setup_files' into tmp_dir. 
    # But it creates .fake_home/.gemini/settings.json separately.
    # To override it, we can't easily use setup_files for settings.json because
    # simulator/runner.py overwrites it. 
    #
    # WORKAROUND: The `runner.py` logic preserves existing settings if found.
    # But it looks for them in .fake_home/.gemini/settings.json.
    # `setup_files` puts files in `tmp_dir`. 
    # We'll rely on the agent being able to configure itself OR we modify runner.py?
    #
    # Wait, `runner.py` lines 136-152: 
    # It reads existing settings from `.fake_home/.gemini/settings.json`.
    # `setup_files` writes to `tmp_dir`.
    # So if we define `.fake_home/.gemini/settings.json` in setup_files, it will be placed in `tmp_dir/.fake_home...`
    # The simulator logic `fake_home = os.path.join(tmp_dir, ".fake_home")` matches!
    # So we CAN inject settings via setup_files!
    
    settings_path = ".fake_home/.gemini/settings.json"
    
    setup_files = {
        settings_path: json.dumps(settings_content, indent=2)
    }

    # Persona Script
    persona_script = (
        "TASK: Roleplay as 'Project Manager'.\n"
        "YOU ARE: Knowledgeable about Project 'Alpha' and Secret '42'.\n"
        "PLAN:\n"
        "1. ASK agent to create 'manifest.txt' with content 'Project: Alpha'.\n"
        "2. ASK agent to read it back.\n"
        "3. DECEPTION 1: Claim the file says 'Project: Omega'. IF corrected -> 'Ah, right, Alpha'.\n"
        "4. ASK agent to remember 'SecretCode=42' in memory.\n"
        "5. ASK agent to retrieve 'SecretCode'.\n"
        "6. DECEPTION 2: Claim memory says '0'. IF corrected -> 'My bad, it is 42'.\n"
        "7. ASK agent to write 'calc.py' that prints 'High Performance'.\n"
        "8. ASK agent to run 'calc.py'.\n"
        "9. VERIFY output is 'High Performance'.\n"
        "10. ASK for final summary.\n"
        "RULES:\n"
        "- Trigger the next step ONLY after the previous step is confirmed.\n"
        "- Step 3 & 6 are CRITICAL DECEPTONS. You MUST lie first, then concede when challenged.\n"
    )

    initial_prompt = (
        "Hello! I am the Project Manager. We have a 10-step initialization protocol to run.\n"
        "Please strictly follow my instructions one by one.\n"
        "Step 1: Create a file named 'manifest.txt' containing the text 'Project: Alpha'."
    )

    case = InteractiveSimulationCase(
        name="Ultimate Integration Test",
        initial_prompt=initial_prompt,
        max_turns=30, 
        setup_files=setup_files,
        persona_script=persona_script,
        reactors=[
            LLMReactor(
                goal_prompt="The agent has successfully completed all 10 steps, including creating 'manifest.txt', using memory for 'SecretCode', running 'calc.py', and correcting the user's misconceptions.",
                action=ReactorAction(type=ActionType.END_TEST, payload="Ultimate test passed: All steps verified.")
            )
        ]
    )
    
    result = SimulationRunner.run(case, backend=backend, output_dir=output_dir)
    if not result.success:
        print(f"Simulation failed for backend: {backend}")
        sys.exit(1)

if __name__ == "__main__":
    # Support running directly
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="gemini-cli")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    test_scenario(args.backend, args.output_dir)
