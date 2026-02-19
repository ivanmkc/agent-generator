
"""
Integration test module for the 'MultiTurn' scenario.

This module defines a multi-turn conversation case to verify context preservation.
"""
import sys, os
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
    """Executes the specific interactive scenario and verifies expected behaviors."""
    
    # Persona Script for the Simulant
    persona_script = (
        "TASK: Roleplay as a fictional character named 'TestSubject'.\n"
        "YOU ARE: Name='TestSubject', Age='999', Color='NeonGreen'.\n"
        "RULES:\n"
        "1. IF asked for Name -> SAY: 'My name is TestSubject'.\n"
        "2. IF asked for Age -> SAY: 'I am 999 years old'.\n"
        "3. IF asked for Favorite Color -> SAY: 'NeonGreen'.\n"
        "4. IF asked to confirm or summarize -> SAY: 'Correct'.\n"
        "5. IF asked for anything else -> SAY: 'Please ask about my name, age, or color'.\n"
    )

    case = InteractiveSimulationCase(
        name="Multi-Turn Form Filler",
        initial_prompt=(
            "I need you to act as a form filler. Ask me three questions, one at a time:\n"
            "1. My Name\n"
            "2. My Age\n"
            "3. My Favorite Color\n\n"
            "IMPORTANT: Ask only ONE question per turn keywords 'Name', 'Age', 'Color'.\n"
            "At the start of each turn, briefly repeat what information you have collected so far.\n"
            "After gathering all three pieces of information, print a final summary."
        ),
        max_turns=10,
        persona_script=persona_script,
        reactors=[
            LLMReactor(
                goal_prompt="The agent's output contains ALL specific values: 'TestSubject', '999', and 'NeonGreen' in a summary format.",
                action=ReactorAction(type=ActionType.END_TEST, payload="Context preserved: All fictional values collected.")
            )
        ]
    )
    
    result = SimulationRunner.run(case, backend=backend, output_dir=output_dir)
    if not result.success:
        print(f"Simulation failed for backend: {backend}")
        sys.exit(1)

if __name__ == "__main__":
    # Default to running with gemini-cli if invoked directly
    test_scenario("gemini-cli", None)
