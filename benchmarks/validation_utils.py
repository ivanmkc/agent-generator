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

"""Utilities for validating generated answers against templates."""

from pathlib import Path
import re
from typing import Any, Optional

import pydantic

from benchmarks.data_models import AnswerTemplate, TraceLogEvent, TraceEventType

# --- Custom Exceptions ---


class ValidationError(Exception):
    """Base class for validation errors."""

    def __init__(
        self, message: str, expected_path: str | None = None
    ):  # pylint: disable=redefined-builtin
        super().__init__(message)
        self.expected_path = expected_path


class TemplateMismatchError(ValidationError):
    """Raised when an answer does not match its template."""


class TraceValidationFailure(ValidationError):
    """Raised when trace log expectations are not met."""


# --- Template Definitions ---


class TemplateInfo(pydantic.BaseModel):
    """Model for storing information about an answer template."""

    regex: str
    description: str
    examples: list[str]


TEMPLATES = {
    AnswerTemplate.CLASS_DEFINITION: TemplateInfo(
        regex=r"^\s*(class\s+)?\w+(\(.*\))?:?\s*$",
        description="A Python class definition or class name.",
        examples=[
            "class MyClass:",
            "class MyClass(object):",
            "MyClass",
        ],
    ),
    AnswerTemplate.PARAMETER_DEFINITION: TemplateInfo(
        regex=r"^\s*\w+(:.*)?$",
        description=(
            "A Python parameter definition (e.g., 'my_param: str' or" " 'my_param')."
        ),
        examples=[
            "my_param: str",
            "my_param",
        ],
    ),
    AnswerTemplate.METHOD_DEFINITION: TemplateInfo(
        regex=(
            r"^(?:\s*@.*\n)*\s*(async\s+)?(def\s+)?\w+(\(.*\n?(?:.*\n)*\s*\))?(?:\s*->\s*.*)?:?\s*$"
        ),
        description="A Python method definition or method name.",
        examples=[
            "def my_method(self):",
            "my_method",
        ],
    ),
    AnswerTemplate.TYPE_ALIAS_DEFINITION: TemplateInfo(
        regex=r"^\s*\w+:\s*TypeAlias\s*=\s*[\s\S]*$",
        description="A Python TypeAlias definition.",
        examples=[
            "MyType: TypeAlias = Union[str, int]",
            "AnotherType: TypeAlias = Callable[[str], None]",
        ],
    ),
    AnswerTemplate.CODE_BLOCK: TemplateInfo(
        regex=r"^[\s\S]*$",  # Matches any code block
        description="A Python code block.",
        examples=[
            "if x > 0:\n    return True",
            "for i in range(10):\n    print(i)",
        ],
    ),
    AnswerTemplate.IDENTIFIER: TemplateInfo(
        regex=r"^\s*\w+\s*$",
        description=("A Python identifier (e.g., a class, variable or function name)."),
        examples=["my_class", "my_variable", "my_function", "my_method"],
    ),
}


def validate_module_path(fully_qualified_class_name: str, expected_paths: list[str]):
    """Validates that the module_path correctly corresponds to the file_path."""
    for expected_path in expected_paths:
        if fully_qualified_class_name == expected_path:
            return

    raise ValidationError(
        f"Module path '{fully_qualified_class_name}' does not exactly match any"
        f" of the expected paths: {expected_paths}",
        expected_path=str(expected_paths),
    )


def validate_answer_against_template(answer: str, template: AnswerTemplate):
    """Validates that the answer matches the regex for the given template."""
    template_info = TEMPLATES.get(template)
    if not template_info:
        raise TemplateMismatchError(f"No template defined for '{template.value}'")

    if not re.match(template_info.regex, answer):
        raise TemplateMismatchError(
            f"Answer does not match template '{template.value}' regex."
        )


def load_snippet(ref: Any) -> str:
    """
    Loads a code snippet from a file, including the file header (imports/setup).

    Args:
        ref: A CodeSnippetRef object or a dict with 'file' and 'section' keys.

    Returns:
        The content of the snippet including the file header.

    Raises:
        FileNotFoundError: If the referenced file does not exist.
        ValueError: If the section is not found in the file.
    """
    # Determine project root (benchmarks/.. -> root)
    project_root = Path(__file__).resolve().parents[1]

    if isinstance(ref, dict):
        file_rel_path = ref["file"]
        section = ref["section"]
    else:
        # Assume CodeSnippetRef object
        file_rel_path = ref.file
        section = ref.section

    file_path = project_root / file_rel_path

    if not file_path.exists():
        raise FileNotFoundError(f"Snippet file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    snippet = []
    in_snippet = False
    found_snippet = False

    for line in lines:
        if "# --8<-- [start:" in line:
            if f"[start:{section}]" in line:
                in_snippet = True
                found_snippet = True
            continue

        if "# --8<-- [end:" in line:
            if f"[end:{section}]" in line:
                in_snippet = False
            continue

        if in_snippet:
            snippet.append(line)

    if not found_snippet:
        raise ValueError(f"Section '{section}' not found in {file_path}")

    import textwrap

    return textwrap.dedent("".join(snippet))

def validate_trace_log_expectations(
    trace_logs: list[TraceLogEvent],
    expected_sub_agent_calls: Optional[list[str]],
    expected_tool_uses: Optional[list[str]],
) -> tuple[bool, Optional[str]]:
    """
    Validates trace logs against expected sub-agent calls and tool uses.

    Args:
        trace_logs: The list of TraceLogEvent objects from the benchmark run.
        expected_sub_agent_calls: An ordered list of expected sub-agent names.
                                  If None or empty, no sub-agent validation is performed.
        expected_tool_uses: An ordered list of expected tool names.
                            If None or empty, no tool use validation is performed.

    Returns:
        A tuple (success, error_message).
        Success is True if all expectations are met, False otherwise.
        error_message is a string detailing the failure, or None on success.
    """
    # Validate expected sub-agent calls
    if expected_sub_agent_calls:
        actual_sub_agent_calls = []
        for event in trace_logs:
            # Assuming sub-agent calls are represented by messages, tool uses, or ADK events from the agent
            if (
                event.type in [TraceEventType.MESSAGE, TraceEventType.TOOL_USE, TraceEventType.ADK_EVENT]
                and (event.role == "model" or event.type == TraceEventType.ADK_EVENT) # ADK_EVENT might not have role "model" explicitly in trace logs but has author
                and event.author != "user" # Exclude user messages
                and event.author # Ensure author is not empty
            ):
                actual_sub_agent_calls.append(event.author)

        if not actual_sub_agent_calls:
            return False, f"Expected sub-agent calls: {expected_sub_agent_calls}, but no sub-agent messages were found."

        expected_idx = 0
        for actual_agent_name in actual_sub_agent_calls:
            if expected_idx < len(expected_sub_agent_calls) and actual_agent_name == expected_sub_agent_calls[expected_idx]:
                expected_idx += 1
        
        if expected_idx < len(expected_sub_agent_calls):
            return False, f"Expected sub-agent '{expected_sub_agent_calls[expected_idx]}' was not called in the expected order."

    # Validate expected tool uses
    if expected_tool_uses:
        actual_tool_uses = []
        for event in trace_logs:
            if event.type == TraceEventType.TOOL_USE and event.tool_name:
                actual_tool_uses.append(event.tool_name)
        
        if not actual_tool_uses:
            return False, f"Expected tool uses: {expected_tool_uses}, but no tool uses were found."

        expected_idx = 0
        for actual_tool_name in actual_tool_uses:
            if expected_idx < len(expected_tool_uses) and actual_tool_name == expected_tool_uses[expected_idx]:
                expected_idx += 1
        
        if expected_idx < len(expected_tool_uses):
            return False, f"Expected tool '{expected_tool_uses[expected_idx]}' was not used in the expected order."

    return True, None

