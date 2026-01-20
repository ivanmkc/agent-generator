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

class TargetType(str, Enum):
    MODULE = "module"
    CLASS = "class"
    METHOD = "method"
    PROPERTY = "property"
    PARAMETER = "parameter"

class ContextNode(pydantic.BaseModel):
    """A node in the associated context tree (flattened)."""
    id: str
    type: str
    probability: float
    usage: int = 0
    parent_id: Optional[str] = None # Used to reconstruct hierarchy if needed

class TargetEntity(pydantic.BaseModel):
    """A hierarchical entity in the codebase targeted for benchmarking."""
    id: str  # Fully Qualified Name (FQN)
    type: TargetType
    name: str
    file_path: str
    usage_score: int = 0
    complexity_score: float = 0.0
    docstring: Optional[str] = None
    parent_id: Optional[str] = None
    # Specific metadata for agents
    signature: Optional[str] = None
    signature_full: Optional[str] = None
    source_code: Optional[str] = None
    # Context Expansion (Flattened list of related entities)
    associated_context: List[ContextNode] = []

class GoldenSnapshot(pydantic.BaseModel):
    """The 'ground truth' capture from the Tracer."""
    target: TargetEntity
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

class MemberInfo(pydantic.BaseModel):
    """Metadata for a method or property."""
    signature: str
    docstring: Optional[str] = None

class RankedTarget(pydantic.BaseModel):
    """The final schema for a ranked target in the YAML file."""
    rank: int
    id: str
    name: str
    file_path: Optional[str] = None
    type: str # String representation of TargetType
    group: str # "Seed", "Dependency", "Orphan"
    usage_score: int
    docstring: Optional[str] = None
    
    methods: Optional[List[MemberInfo]] = None
    properties: Optional[List[MemberInfo]] = None
    
    inherited_methods: Optional[Dict[str, List[MemberInfo]]] = None
    inherited_properties: Optional[Dict[str, List[MemberInfo]]] = None
    
    omitted_inherited_members_from: Optional[List[str]] = None
