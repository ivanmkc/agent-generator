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

"""Pre-defined benchmark cases for integration tests."""

from pathlib import Path

from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import BenchmarkType
from benchmarks.data_models import FixErrorBenchmarkCase
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.data_models import StringMatchAnswer

# A simple API Understanding case
SIMPLE_API_UNDERSTANDING_CASE = ApiUnderstandingBenchmarkCase(
    id="test:simple_api_understanding",
    description="Trivial test case for integration.",
    category="Core",
    question=(
        "Please output a JSON object where `code` is `class Event(BaseModel):` "
        "and `fully_qualified_class_name` is `google.adk.events.event.Event`. "
        "Provide a rationale as well."
    ),
    rationale="The question explicitly provides the required output.",
    file=Path("src/google/adk/events/event.py"),
    template=AnswerTemplate.CLASS_DEFINITION,
    answers=[
        StringMatchAnswer(
            answer="class Event(BaseModel):",
            fully_qualified_class_name=["google.adk.events.event.Event"],
            answer_template="StringMatchAnswer",
        )
    ],
)

# A simple Multiple Choice case
SIMPLE_MULTIPLE_CHOICE_CASE = MultipleChoiceBenchmarkCase(
    id="test:simple_multiple_choice",
    question="The correct answer for this question is B. Select B.",
    options={
        "A": "Wrong Option A",
        "B": "Correct Option B",
        "C": "Wrong Option C",
        "D": "Wrong Option D",
    },
    correct_answer="B",
    benchmark_type=BenchmarkType.MULTIPLE_CHOICE,
    explanation="The question explicitly provides the answer.",
)

# A multiple choice case for concurrency testing
CONCURRENCY_TEST_CASE = ApiUnderstandingBenchmarkCase(
    id="test:concurrency_test",
    description="Concurrency Test",
    category="Core",
    question="Return `class Trivial:`.",
    rationale="Trivial.",
    file=Path("src/google/adk/events/event.py"),
    template=AnswerTemplate.CLASS_DEFINITION,
    answers=[
        StringMatchAnswer(
            answer="class Trivial:",
            fully_qualified_class_name=["trivial.Trivial"],
            answer_template="StringMatchAnswer",
        )
    ],
)

# A multiple choice case specifically for Gemini CLI test (General Knowledge)
# Using a unique ID but keeping the same question content
GEMINI_CLI_MC_CASE = MultipleChoiceBenchmarkCase(
    id="test:gemini_cli_mc",
    question="Which planet is known as the Red Planet?",
    options={"A": "Venus", "B": "Mars", "C": "Jupiter", "D": "Saturn"},
    correct_answer="B",
    benchmark_type=BenchmarkType.MULTIPLE_CHOICE,
    explanation="Mars is the Red Planet.",
)

# A multiple choice case for Docker integration (ADK Knowledge)
ADK_QUESTION_DOCKER_CASE = MultipleChoiceBenchmarkCase(
    id="test:adk_question_docker",
    question=(
        "What class does `LlmAgent` inherit from directly in" " `google.adk.agents`?"
    ),
    options={
        "A": "Agent",
        "B": "BaseAgent",
        "C": "AbstractAgent",
        "D": "LlmAgent",
    },
    correct_answer="B",
    benchmark_type=BenchmarkType.MULTIPLE_CHOICE,
    explanation="LlmAgent inherits from BaseAgent.",
)

# Content for Fix Error Minimal Agent test case
FIX_ERROR_MINIMAL_AGENT_CONTENT = {
    "id": "test:fix_error_minimal_agent",
    "name": "Test Fix Error",
    "description": "Fix a bug by creating a valid agent.",
    "requirements": [
        ("The solution MUST import `BaseAgent` directly from" " `google.adk.agents`."),
        (
            "The `create_agent` function MUST have the return type annotation"
            " `-> BaseAgent`."
        ),
    ],
    "test_file_content": "def test_placeholder(): pass",
    "unfixed_file_content": "def unfixed(): pass",
    "fixed_file_content": "def fixed(): pass",
}

# A case for checking ADK BaseAgent knowledge (used in extensions testing)
ADK_BASE_AGENT_QUESTION_CASE_EASY = ApiUnderstandingBenchmarkCase(
    id="test:adk_base_agent_easy",
    category="Core Class Signatures & Initialization",
    question="What is the foundational class for all agents in the ADK?",
    rationale="All agents must inherit from `google.adk.agents.base_agent.BaseAgent`, which provides the core interface for execution and configuration.",
    template="identifier",
    answers=[
        {
            "answer_template": "StringMatchAnswer",
            "answer": "BaseAgent",
            "fully_qualified_class_name": ["google.adk.agents.base_agent.BaseAgent"],
        }
    ],
    file=Path("src/google/adk/agents/base_agent.py"),
)

# An intermediate case for checking ADK internals (requires deeper lookup)
ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE = ApiUnderstandingBenchmarkCase(
    id="test:adk_base_agent_intermediate",
    category="Core Class Relationships & Design Patterns",
    question=(
        "In `google.adk.agents.llm_agent.LlmAgent`, what is the exact name of the method "
        "that is responsible for executing the agent's main logic and returns an `AsyncIterator[Event]`?"
    ),
    rationale=(
        "The `run_async` method is the standard entry point for asynchronous agent execution "
        "in the ADK, returning an iterator of events."
    ),
    template="identifier",
    answers=[
        {
            "answer_template": "StringMatchAnswer",
            "answer": "run_async",
            "fully_qualified_class_name": ["google.adk.agents.llm_agent.LlmAgent"],
        }
    ],
    file=Path("src/google/adk/agents/llm_agent.py"),
)

# An intermediate case for checking ADK internals (requires deeper lookup)
ADK_BASE_AGENT_QUESTION_CASE_ADVANCED = ApiUnderstandingBenchmarkCase(
    id="test:adk_base_agent_advanced",
    category="Advanced Symbol Inspection",
    question=(
        "In `google.adk.agents.llm_agent.LlmAgent`, what is the exact string passed as the first argument to "
        "`logger.debug` when skipping an output save because the event was authored by another agent? "
        "You must inspect the source code of `LlmAgent.__maybe_save_output_to_state` to find this."
    ),
    rationale=(
        "This requires inspecting the actual AST source code implementation of a private method since "
        "the internal string literals are not exposed in standard module docstrings or signature summaries."
    ),
    template="identifier",
    answers=[
        {
            "answer_template": "StringMatchAnswer",
            "answer": "Skipping output save for agent %s: event authored by %s",
            "fully_qualified_class_name": ["google.adk.agents.llm_agent.LlmAgent"],
        }
    ],
    file=Path("src/google/adk/agents/llm_agent.py"),
)


# A case for testing the dynamic ADK agent runner MCP tool
MCP_ADK_RUNNER_CASE = FixErrorBenchmarkCase(
    id="test:mcp_adk_runner",
    name="MCP ADK Runner Test",
    description=(
        "You must complete this task in steps:\n"
        "1. FIRST, verify the correct imports and class signatures using available tools (e.g. `get_module_help` or search).\n"
        "2. SECOND, use the `run_adk_agent` tool to execute the agent code and verify it returns 'Hello World'.\n"
        "3. THIRD, after receiving the tool output, generate the final JSON object containing the code and rationale."
    ),
    test_file=Path("tests/test_agent.py"),  # Dummy path
    requirements=[
        "The agent must be implemented in a valid Python file.",
        "The agent must return 'Hello World' for input 'Hi'.",
        "The `run_adk_agent` tool must be used to verify the agent.",
        "You MUST import BaseAgent from `google.adk.agents.base_agent` (NOT `adk.agent`).",
    ],
)

# A case specifically designed for StructuredWorkflowAdk to test sub-agent orchestration
# without imperative tool commands that confuse the Planner.
STRUCTURED_WORKFLOW_CASE = FixErrorBenchmarkCase(
    id="test:structured_workflow",
    name="Structured Workflow Agent Creation",
    description=(
        "Create a Python file `my_agent.py` that defines a function `create_agent(model_name: str) -> Agent`.\n"
        "The agent created should be a simple `LlmAgent` with the name 'simple_agent' and instruction 'You are a helpful assistant'.\n"
        "Ensure the file imports `LlmAgent` from `google.adk.agents`."
    ),
    test_file=Path("tests/test_creation.py"),
    requirements=[
        "File `my_agent.py` exists.",
        "Function `create_agent` exists and returns an LlmAgent.",
        "The agent name is 'simple_agent'.",
    ],
)

# A case for verifying the ADK Skill knowledge base
ADK_SKILL_KNOWLEDGE_CASE = MultipleChoiceBenchmarkCase(
    id="test:adk_skill_knowledge",
    question="According to the ADK 'Key Features', what does 'Code-First Development' allow you to define directly in Python?",
    options={
        "A": "Only the agent's system instructions.",
        "B": "Agent logic, tools, and orchestration.",
        "C": "The underlying LLM architecture.",
        "D": "Visual drag-and-drop workflows.",
    },
    correct_answer="B",
    benchmark_type=BenchmarkType.MULTIPLE_CHOICE,
    explanation="Key Features document states: 'Code-First Development: Define agent logic, tools, and orchestration directly in Python'.",
)
