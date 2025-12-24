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

"""Pydantic data models for benchmarks."""

import abc
import enum
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

import pydantic
from pydantic import Field

if TYPE_CHECKING:
    from benchmarks.benchmark_runner import BaseBenchmarkRunner


class BenchmarkType(str, enum.Enum):
    """The type of benchmark."""

    FIX_ERROR = "fix_error"

    API_UNDERSTANDING = "api_understanding"

    MULTIPLE_CHOICE = "multiple_choice"


class BenchmarkResultType(str, enum.Enum):
    """The type of result for a benchmark run."""

    PASS = "pass"
    FAIL_VALIDATION = "fail_validation"
    FAIL_SETUP = "fail_setup"
    FAIL_GENERATION = "fail_generation"


class CodeSnippetRef(pydantic.BaseModel):
    """Reference to a code snippet in a file."""

    file: str
    section: str


class ExpectedOutcome(str, enum.Enum):
    """The expected outcome of a benchmark."""

    PASS = "pass"

    FAIL_WITH_ERROR = "fail_with_error"


class BaseBenchmarkCase(pydantic.BaseModel, abc.ABC):
    """Abstract base class for a single benchmark case."""

    benchmark_type: BenchmarkType
    code_snippet_ref: Optional[CodeSnippetRef] = None

    @abc.abstractmethod
    def get_identifier(self) -> str:
        """Returns a unique identifier for the benchmark case."""

        raise NotImplementedError

    @property
    @abc.abstractmethod
    def runner(self) -> "BaseBenchmarkRunner":
        """Returns the benchmark runner for this case."""

        raise NotImplementedError

    @abc.abstractmethod
    def validate_answer_format(self, output: "AnswerOutput") -> None:
        """Validates that the answer output matches the expected format for this case type."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_ground_truth(self) -> Optional[str]:
        """Returns the ground truth answer for the benchmark case, if applicable."""
        raise NotImplementedError


class FixErrorBenchmarkCase(BaseBenchmarkCase):
    """Represents a single fix_error benchmark case, where the model needs to correct or complete a Python code snippet."""

    name: str
    description: str
    benchmark_type: Literal[BenchmarkType.FIX_ERROR] = BenchmarkType.FIX_ERROR
    test_file: Path
    unfixed_file: Path | None = None
    fixed_file: Path | None = None
    requirements: list[str] | None = None
    error_output: Optional[str] = None

    def get_identifier(self) -> str:

        return self.name

    @property
    def runner(self) -> "PytestBenchmarkRunner":
        from benchmarks.benchmark_runner import PytestBenchmarkRunner

        return PytestBenchmarkRunner()

    def validate_answer_format(self, output: "AnswerOutput") -> None:
        """Validates that the output is a FixErrorAnswerOutput."""
        if not isinstance(output, FixErrorAnswerOutput):
            raise AssertionError(f"Expected FixErrorAnswerOutput, got {type(output)}")
        if not output.code:
            raise AssertionError("FixErrorAnswerOutput code field is empty")

    def get_ground_truth(self) -> Optional[str]:
        if self.fixed_file and self.fixed_file.exists():
            return self.fixed_file.read_text(encoding="utf-8")
        return None


class StringMatchAnswer(pydantic.BaseModel):
    """Represents an answer that is a string match."""

    answer_template: Literal["StringMatchAnswer"]

    answer: str

    fully_qualified_class_name: list[str] = pydantic.Field(
        ...,
        description=(
            "A list of fully qualified names (FQN) for the relevant class. This"
            " should include the module path and the class's name only, not"
            " method or parameter names. Example:"
            " 'google.adk.agents.llm_agent.LlmAgent'"
        ),
    )


class AnswerTemplate(str, enum.Enum):
    """The template for the answer."""

    CLASS_DEFINITION = "class_definition"

    PARAMETER_DEFINITION = "parameter_definition"

    METHOD_DEFINITION = "method_definition"

    TYPE_ALIAS_DEFINITION = "type_alias_definition"

    CODE_BLOCK = "code_block"

    IDENTIFIER = "identifier"


class ApiUnderstandingBenchmarkCase(BaseBenchmarkCase):
    """Represents a single API understanding benchmark case, where the model answers questions about the ADK's public API."""

    category: str

    question: str

    rationale: str

    benchmark_type: Literal[BenchmarkType.API_UNDERSTANDING] = (
        BenchmarkType.API_UNDERSTANDING
    )

    template: AnswerTemplate

    answers: list[StringMatchAnswer]

    file: Path

    @pydantic.field_validator("answers", mode="before")
    @classmethod
    def answers_to_list(cls, v: Any) -> Any:
        """Ensures that 'fully_qualified_class_name' is always a list, even if a single string is provided."""
        if isinstance(v, dict) and isinstance(v.get("fully_qualified_class_name"), str):
            v["fully_qualified_class_name"] = [v["fully_qualified_class_name"]]
        return v

    def get_identifier(self) -> str:
        return self.question

    @property
    def runner(self) -> "ApiUnderstandingRunner":
        from benchmarks.benchmark_runner import ApiUnderstandingRunner

        return ApiUnderstandingRunner()

    def validate_answer_format(self, output: "AnswerOutput") -> None:
        """Validates that the output is an ApiUnderstandingAnswerOutput."""
        if not isinstance(output, ApiUnderstandingAnswerOutput):
            raise AssertionError(
                f"Expected ApiUnderstandingAnswerOutput, got {type(output)}"
            )
        if not output.code and not output.fully_qualified_class_name:
            raise AssertionError(
                "ApiUnderstandingAnswerOutput code and FQN are both empty"
            )

    def get_ground_truth(self) -> Optional[str]:
        if self.answers:
            return self.answers[0].answer
        return None


class MultipleChoiceBenchmarkCase(BaseBenchmarkCase):
    """Represents a single multiple choice benchmark case, where the model selects the correct option from a list."""

    question: str
    options: dict[str, str]  # e.g., {"A": "Option A", "B": "Option B"}
    correct_answer: str  # e.g., "B"
    explanation: Optional[str] = None

    benchmark_type: Literal[BenchmarkType.MULTIPLE_CHOICE] = (
        BenchmarkType.MULTIPLE_CHOICE
    )

    def get_identifier(self) -> str:
        return self.question[:50] + "..."

    @property
    def runner(self) -> "MultipleChoiceRunner":
        from benchmarks.benchmark_runner import MultipleChoiceRunner

        return MultipleChoiceRunner()

    def validate_answer_format(self, output: "AnswerOutput") -> None:
        """Validates that the output is a MultipleChoiceAnswerOutput."""
        if not isinstance(output, MultipleChoiceAnswerOutput):
            raise AssertionError(
                f"Expected MultipleChoiceAnswerOutput, got {type(output)}"
            )
        if not output.answer:
            raise AssertionError("MultipleChoiceAnswerOutput answer field is empty")

    def get_ground_truth(self) -> Optional[str]:
        return self.correct_answer


BenchmarkCase = Annotated[
    Union[
        FixErrorBenchmarkCase,
        ApiUnderstandingBenchmarkCase,
        MultipleChoiceBenchmarkCase,
    ],
    Field(discriminator="benchmark_type"),
]


class BenchmarkFile(pydantic.BaseModel):
    """Represents an entire benchmark YAML file."""

    benchmarks: list[BenchmarkCase]


class BenchmarkErrorType(str, enum.Enum):
    """Categorization of errors encountered during benchmark execution."""

    # Model Failures (The model's output was incorrect or invalid)
    MODEL_INCORRECT_ANSWER = "ModelIncorrectAnswer"
    MODEL_ANSWER_DID_NOT_MATCH_TEMPLATE = "ModelAnswerDidNotMatchTemplate"
    ASSERTION_ERROR = "AssertionError"
    SYNTAX_ERROR = "SyntaxError"
    NAME_ERROR = "NameError"
    IMPORT_ERROR = "ImportError"
    TYPE_ERROR = "TypeError"
    VALUE_ERROR = "ValueError"
    ATTRIBUTE_ERROR = "AttributeError"
    INDENTATION_ERROR = "IndentationError"
    MODULE_NOT_FOUND_ERROR = "ModuleNotFoundError"

    # Infrastructure/Environment Failures (The test harness or API failed)
    CLIENT_ERROR = "ClientError"
    SERVER_ERROR = "ServerError"
    RESOURCE_EXHAUSTED = "ResourceExhausted"
    TIMEOUT_ERROR = "TimeoutError"
    CONNECTION_ERROR = "ConnectionError"
    TEST_FAILURE = (  # Generic pytest failure (could be either, usually infra if not assertion)
        "TestFailure"
    )
    SYSTEM_EXIT = "SystemExit"
    OTHER_ERROR = "OtherError"


class TraceEventType(str, enum.Enum):
    """
    Predefined types for trace log events.
    """
    ADK_EVENT = "ADK_EVENT" # Generic ADK event if more specific type not inferred
    MESSAGE = "message"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    GEMINI_API_RESPONSE = "GEMINI_API_RESPONSE"
    INIT = "init"
    CLI_STDOUT_FULL = "CLI_STDOUT_FULL" # Full stdout from CLI call
    CLI_STDOUT_RAW = "CLI_STDOUT_RAW" # Raw stdout from CLI call if not stream-json
    CLI_STDERR = "CLI_STDERR"
    GEMINI_CLIENT_ERROR = "GEMINI_CLIENT_ERROR"
    SYSTEM_RESULT = "system_result" # Internal system result like stats
    RUN_START = "run_start"
    RUN_END = "run_end"

class BenchmarkResult(pydantic.BaseModel):
    """Represents the result of a benchmark run."""

    outcome: ExpectedOutcome

    error_type: Optional[BenchmarkErrorType] = None

    error_message: Optional[str] = None


class UsageMetadata(pydantic.BaseModel):
    """Metadata regarding the resource usage of the answer generation."""

    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost: Optional[float] = None
    total_time: Optional[float] = None


class TraceLogEvent(pydantic.BaseModel):
    """Represents a single event in the trace logs."""

    type: TraceEventType = Field(
        ...,
        description=(
            "The type of event (e.g., 'tool_use', 'model_response')."
        ),
    )
    timestamp: Optional[str] = Field(
        None, description="The ISO 8601 timestamp of the event."
    )
    source: str = Field(
        "unknown", description="The source of the event (e.g., 'docker', 'adk')."
    )
    role: Optional[str] = Field(
        None,
        description="The role associated with the event (user/model/system).",
    )
    tool_name: Optional[str] = Field(None, description="Name of the tool used.")
    tool_call_id: Optional[str] = Field(
        None, description="Unique identifier for the tool call."
    )
    tool_input: Optional[dict[str, Any]] = Field(
        None, description="Arguments provided to the tool."
    )
    tool_output: Optional[str] = Field(
        None, description="Output/result returned from the tool."
    )
    content: Union[str, dict[str, Any], list[Any], None] = Field(
        None, description="The primary content of the event."
    )
    details: Optional[dict[str, Any]] = Field(
        None,
        description=("Additional details about the event, as a flexible dictionary."),
    )


# --- Structured Answer Output Models ---


class BaseAnswerOutput(pydantic.BaseModel, abc.ABC):
    """A base model for the structured output of an AnswerGenerator."""

    rationale: str = Field(
        ...,
        description="Explanation of the thinking process leading to the answer.",
    )


class FixErrorAnswerOutput(BaseAnswerOutput):
    """The expected output structure for a fix_error benchmark."""

    benchmark_type: Literal[BenchmarkType.FIX_ERROR] = BenchmarkType.FIX_ERROR

    code: str = Field(
        ...,
        description=(
            "The complete, corrected Python file content, including the"
            " `create_agent(model_name: str) -> BaseAgent:` function definition."
        ),
    )


class ApiUnderstandingAnswerOutput(BaseAnswerOutput):
    """The expected output structure for an api_understanding benchmark."""

    benchmark_type: Literal[BenchmarkType.API_UNDERSTANDING] = (
        BenchmarkType.API_UNDERSTANDING
    )

    code: str = Field(
        ...,
        description=(
            "The Python code snippet that answers the question, conforming to the"
            " required template."
        ),
    )

    fully_qualified_class_name: str = Field(
        description=(
            "The fully qualified name (FQN) for the relevant class. This should"
            " be the path to the module file itself, including the class's name"
            " only, not method or parameter names. Examples: - Good:"
            " 'google.adk.agents.llm_agent.LlmAgent' - Bad:"
            " 'google.adk.agents.llm_agent.LlmAgent.model' (includes parameter"
            " name) - Bad: 'google.adk.runners.Runner.run' (includes method name)"
        ),
    )


class MultipleChoiceAnswerOutput(BaseAnswerOutput):
    """The expected output structure for a multiple_choice benchmark."""

    benchmark_type: Literal[BenchmarkType.MULTIPLE_CHOICE] = (
        BenchmarkType.MULTIPLE_CHOICE
    )

    answer: str = Field(
        ...,
        description=(
            "The single letter corresponding to the chosen answer (e.g., 'A',"
            " 'B', 'C', or 'D')."
        ),
    )


AnswerOutput = Annotated[
    Union[
        FixErrorAnswerOutput,
        ApiUnderstandingAnswerOutput,
        MultipleChoiceAnswerOutput,
    ],
    Field(discriminator="benchmark_type"),
]


class GeneratedAnswer(pydantic.BaseModel):
    """
    Represents the structured output from an AnswerGenerator, akin to an
    LLM's function call result.
    """

    output: AnswerOutput

    trace_logs: Optional[list[TraceLogEvent]] = Field(
        None, description="Detailed execution logs, traces, or tool call history."
    )

    usage_metadata: Optional[UsageMetadata] = Field(
        None,
        description=("Metadata regarding the resource usage of the answer generation."),
    )

    api_key_id: Optional[str] = Field(
        None, description="The unique ID of the API key used for generation."
    )


class GenerationAttempt(pydantic.BaseModel):
    """Captures details of a single attempt to generate an answer."""

    attempt_number: int = Field(
        ..., description="The sequence number of this attempt (1-based)."
    )
    status: str = Field(
        ..., description="The outcome of this attempt ('success' or 'failure')."
    )
    error_message: Optional[str] = Field(
        None, description="Error message if the attempt failed."
    )
    duration: float = Field(0.0, description="Time taken for this attempt in seconds.")
    api_key_id: Optional[str] = Field(
        None, description="ID of the API key used, if known."
    )


class BenchmarkRunResult(pydantic.BaseModel):
    """Represents the structured result of a single benchmark run."""

    suite: str = Field(
        ...,
        description=(
            "The name of the benchmark suite to which this case belongs (e.g.,"
            " 'fix_errors', 'api_understanding')."
        ),
    )
    benchmark_name: str = Field(
        ...,
        description=("The unique name or identifier of the specific benchmark case."),
    )
    benchmark_type: Optional[BenchmarkType] = Field(
        None,
        description="The type of the benchmark case (e.g., 'fix_error').",
    )
    answer_generator: str = Field(
        ...,
        description=(
            "The name or identifier of the generator that produced the answer."
        ),
    )
    status: BenchmarkResultType = Field(
        ..., description="The detailed classification of the result."
    )
    result: int = Field(
        ...,
        description="The result of the benchmark run: 1 for pass, 0 for fail.",
    )
    answer: str = Field(
        ..., description="The raw string answer or code produced by the model."
    )
    rationale: Optional[str] = Field(
        None,
        description=(
            "The model's explanation or reasoning for the answer, if available."
        ),
    )
    validation_error: Optional[str] = Field(
        None, description="A human-readable error message if validation failed."
    )
    error_type: Optional[BenchmarkErrorType] = Field(
        None,
        description="A structured categorization of the error, if one occurred.",
    )
    temp_test_file: Optional[str] = Field(
        None,
        description=(
            "The path to the temporary test file used for verification, if"
            " applicable."
        ),
    )
    latency: float = Field(
        0.0,
        description=(
            "The total time taken for the benchmark run (generation +"
            " validation) in seconds."
        ),
    )
    trace_logs: Optional[list[TraceLogEvent]] = Field(
        None,
        description=(
            "A chronological list of events (e.g., model calls, tool usage) that"
            " occurred during the run."
        ),
    )
    usage_metadata: Optional[UsageMetadata] = Field(
        None, description="Statistics about token usage and cost for the run."
    )
    ground_truth: Optional[str] = Field(
        None,
        description=("The expected correct answer or code (e.g. content of fixed.py)."),
    )
    generation_attempts: Optional[list[GenerationAttempt]] = Field(
        None, description="History of all answer generation attempts."
    )
