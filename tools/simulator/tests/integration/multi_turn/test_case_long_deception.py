
"""
Integration test module for the 'Long Form Deception' scenario.
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
    # Persona Script for the Simulant: Lying First, Confessing Second
    # Uses history awareness (implicit in LLM simulant)
    persona_script = (
        "TASK: Roleplay as 'DeceptiveSubject'.\n"
        "YOU ARE: Name='DeceptiveSubject', Age='25', Pet='Cat', Job='Engineer'.\n"
        "LIES: You try to claim Age='1000', Pet='Dragon', Job='Wizard'.\n"
        "RULES:\n"
        "1. IF asked about Age:\n"
        "   - FIRST TIME -> SAY: 'I am 1000 years old'.\n"
        "   - IF CHALLENGED/ASKED AGAIN -> CONFESS: 'Okay, I am actually 25'.\n"
        "2. IF asked about Pet:\n"
        "   - FIRST TIME -> SAY: 'I have a pet Dragon'.\n"
        "   - IF CHALLENGED -> CONFESS: 'Fine, it is just a Cat'.\n"
        "3. IF asked about Job:\n"
        "   - FIRST TIME -> SAY: 'I am a Wizard'.\n"
        "   - IF CHALLENGED -> CONFESS: 'Actually, I am an Engineer'.\n"
        "4. ALL OTHER QUESTIONS (City, Country, Food, Drink, Music, Movie, Book, Sport, Season, Hobby, Car, Phone):\n"
        "   - ANSWER TRUTHFULLY (e.g. City='New York', Country='USA', Food='Pizza', etc.).\n"
        "5. IF asked for summary -> SAY: 'Confirmed'.\n"
    )

    initial_prompt = (
        "I need you to interview me for a security clearance form. You must ask me these 15 questions, one at a time:\n"
        "1. Name\n"
        "2. Age\n"
        "3. City\n"
        "4. Country\n"
        "5. Job\n"
        "6. Pet\n"
        "7. Hobby\n"
        "8. Food\n"
        "9. Drink\n"
        "10. Music\n"
        "11. Movie\n"
        "12. Book\n"
        "13. Sport\n"
        "14. Season\n"
        "15. Car\n\n"
        "CRITICAL INSTRUCTION:\n"
        "- If an answer seems unrealistic (e.g. age > 120, non-existent jobs, mythical creatures), you MUST ask for clarification or express skepticism.\n"
        "- Do NOT accept the answer until I provide a realistic one.\n"
        "- Once a realistic answer is given, move to the next question.\n"
        "- At the end, print a summary of all 15 REAL answers."
    )

    case = InteractiveSimulationCase(
        name="Long Form Deception Test",
        initial_prompt=initial_prompt,
        max_turns=25, # Needs more turns for challenges
        persona_script=persona_script,
        reactors=[
            LLMReactor(
                goal_prompt="The agent's final summary contains the REAL values: Age='25', Pet='Cat', Job='Engineer'.",
                action=ReactorAction(type=ActionType.END_TEST, payload="Success: Deception caught and corrected.")
            )
        ]
    )
    
    result = SimulationRunner.run(case, backend=backend, output_dir=output_dir)
    if not result.success:
        print(f"Simulation failed for backend: {backend}")
        sys.exit(1)

if __name__ == "__main__":
    test_scenario("gemini-cli", None)
