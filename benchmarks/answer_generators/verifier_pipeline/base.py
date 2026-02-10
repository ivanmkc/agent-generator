from typing import List, Optional
from google.adk.agents import SequentialAgent, LlmAgent
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, CodeBasedTeardownAgent
from .models import VerificationVerdict

class VerdictSynthesizerAgent(LlmAgent):
    """
    Synthesizes the final verdict based on proof results.
    """
    def __init__(self, model):
        super().__init__(
            name="verdict_synthesizer",
            model=model,
            tools=[],
            output_key="final_response",
            output_schema=VerificationVerdict,
            instruction=(
                "You are the Verdict Synthesizer.\n"
                "Input: Original Question, Ground Truth, and Empirical Proof Results (review conversation history).\n"
                "Task: Determine the quality of the question.\n"
                "\n"
                "Logic for Multiple Choice:\n"
                "- VALID: The 'Correct' option was proven valid (code works), AND all 'Distractor' options were proven invalid (code fails or raises error).\n"
                "- AMBIGUOUS: Multiple options were proven valid (distractors failed to fail).\n"
                "- INCORRECT: The 'Correct' option failed (code did not work).\n"
                "\n"
                "Logic for Other Types:\n"
                "- VALID: The implementation or regex correctly achieves the goal described in the prompt.\n"
                "- INCORRECT: The implementation or regex misses edge cases or fails execution.\n"
                "\n"
                "You must strictly output the designated JSON schema, with a verdict of 'Valid', 'Ambiguous', 'Incorrect', or 'Unknown', and provide a detailed breakdown per option in the evaluated_claims list."
            )
        )
