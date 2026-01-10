# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Data models for Prismatic Evaluation."""

from typing import Any, Dict, List, Optional
from enum import Enum
import pydantic

class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL_CRASH = "FAIL_CRASH"
    FAIL_ASSERTION = "FAIL_ASSERTION"
    FAIL_TIMEOUT = "FAIL_TIMEOUT"

class TargetMethod(pydantic.BaseModel):
    """Represents a method or function identified by the Scanner."""
    file_path: str
    class_name: Optional[str] = None
    parent_classes: List[str] = [] # For hierarchy mapping
    method_name: str
    code_signature: str
    docstring: Optional[str] = None
    complexity_score: float = 0.0
    dependencies: List[str] = [] # Files imported by this file

class GoldenSnapshot(pydantic.BaseModel):
    """The 'ground truth' capture from the Tracer."""
    target: TargetMethod
    valid_usage_code: str  # Option A (The correct code)
    stdout: str
    return_value: str  # String representation
    local_vars: Dict[str, str]  # Captured local variables
    execution_time: float

class ObserverOutput(pydantic.BaseModel):
    """Output from the Observer agent."""
    status: str  # SUCCESS or FAILED
    rationale: str
    code_generated: Optional[str] = None

class DistractorOption(pydantic.BaseModel):
    """A generated distractor option (B, C, D)."""
    code: str
    mutation_type: str  # e.g., "Semantic", "Context Poisoning", "SAFIM"
    mutation_description: str
    diff_from_golden: str  # Diff string

class SaboteurOutput(pydantic.BaseModel):
    """Output from the Saboteur agent."""
    mutants: List[DistractorOption]
    status: str # SUCCESS or FAILED

class BenchmarkCandidate(pydantic.BaseModel):
    """A fully assembled candidate question."""
    snapshot: GoldenSnapshot
    distractors: List[DistractorOption]
    question_text: str
    metadata: Dict[str, Any]  # Difficulty, estimated IRT params, etc.

class BenchmarkResult(pydantic.BaseModel):
    """Result of running a candidate through validation."""
    candidate: BenchmarkCandidate
    valid: bool
    validation_logs: List[str]
    uniqueness_score: float = 0.0