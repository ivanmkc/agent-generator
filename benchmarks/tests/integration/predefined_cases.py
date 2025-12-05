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
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.data_models import StringMatchAnswer

# A simple API Understanding case
SIMPLE_API_UNDERSTANDING_CASE = ApiUnderstandingBenchmarkCase(
    name="Trivial Test Case",
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
    name="Concurrency Test",
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
GEMINI_CLI_MC_CASE = MultipleChoiceBenchmarkCase(
    question="Which planet is known as the Red Planet?",
    options={"A": "Venus", "B": "Mars", "C": "Jupiter", "D": "Saturn"},
    correct_answer="B",
    benchmark_type=BenchmarkType.MULTIPLE_CHOICE,
    explanation="Mars is the Red Planet.",
)

# A multiple choice case for Docker integration (ADK Knowledge)
ADK_QUESTION_DOCKER_CASE = MultipleChoiceBenchmarkCase(
    question=(
        "What is the name of the base class for all agents in"
        " `google.adk.agents`?"
    ),
    options={
        "A": "Agent",
        "B": "BaseAgent",
        "C": "AbstractAgent",
        "D": "LlmAgent",
    },
    correct_answer="B",
    benchmark_type=BenchmarkType.MULTIPLE_CHOICE,
    explanation="BaseAgent is the base class.",
)

# Content for Fix Error Minimal Agent test case
FIX_ERROR_MINIMAL_AGENT_CONTENT = {
    "name": "Test Fix Error",
    "description": "Fix a bug by creating a valid agent.",
    "requirements": [
        (
            "The solution MUST import `BaseAgent` directly from"
            " `google.adk.agents`."
        ),
        (
            "The `create_agent` function MUST have the return type annotation"
            " `-> BaseAgent`."
        ),
    ],
    "test_file_content": "def test_placeholder(): pass",
    "unfixed_file_content": "def unfixed(): pass",
    "fixed_file_content": "def fixed(): pass",
}
