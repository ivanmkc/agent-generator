from pydantic import BaseModel, Field
from typing import List, Optional

class Claim(BaseModel):
    """Represents a testable hypothesis derived from a multiple-choice option."""
    option: str = Field(description="The option identifier (e.g., A, B, C, D)")
    hypothesis: str = Field(description="The formal hypothesis to test to prove whether this option is correct or incorrect.")
    code_hint: str = Field(description="Python snippet or pytest structure that could test this hypothesis.")

class ClaimList(BaseModel):
    """A collection of claims to be verified."""
    claims: List[Claim] = Field(description="List of claims extracted from the benchmark question options.")

class EvaluatedClaim(BaseModel):
    """The empirical evaluation result for a single claim/option."""
    option: str = Field(description="The option identifier (e.g., A, B, C, D)")
    verdict: str = Field(description="The empirical verdict for this specific claim (e.g., True/Correct vs False/Incorrect)")
    explanation: str = Field(description="Explanation of why this claim was proven true or false based on the pytest results")

class VerificationVerdict(BaseModel):
    """The final verdict on the quality and correctness of the benchmark question."""
    verdict: str = Field(description="Must be one of: Valid, Ambiguous, Incorrect, Unknown")
    details: str = Field(description="Detailed rationale for why the chosen verdict was determined based on the empirical proof.")
    evaluated_claims: Optional[List[EvaluatedClaim]] = Field(default=None, description="Detailed verification results and explanations for each evaluated claim/option.")
    suggested_fix: Optional[str] = Field(default=None, description="If the verdict is not Valid, a proposed fix for the benchmark data definitions.")
