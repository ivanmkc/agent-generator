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

"""Unit tests for LlmAnswerGenerator's context file handling."""

import pytest
from pathlib import Path
from typing import List

from benchmarks.answer_generators.llm_base import LlmAnswerGenerator
from benchmarks.data_models import BaseBenchmarkCase, GeneratedAnswer


# Mock concrete implementation of LlmAnswerGenerator for testing purposes
class MockLlmAnswerGenerator(LlmAnswerGenerator):

    def __init__(self, context: str | Path | None = None):
        super().__init__(context=context)

    @property
    def name(self) -> str:
        return "MockLlmAnswerGenerator"

    async def generate_answer(
        self, benchmark_case: BaseBenchmarkCase
    ) -> GeneratedAnswer:
        # Not relevant for this test, just implement to satisfy abstract class
        raise NotImplementedError("generate_answer not implemented for mock")


def test_get_context_content_file_not_found():
    """Tests that FileNotFoundError is raised for a non-existent context file."""
    non_existent_path = Path("non_existent_context_file.txt")
    # Ensure it truly does not exist
    if non_existent_path.exists():
        non_existent_path.unlink()

    generator = MockLlmAnswerGenerator(context=non_existent_path)

    with pytest.raises(
        FileNotFoundError, match=f"Context file not found: {non_existent_path}"
    ):
        generator._get_context_content()


def test_get_context_content_no_context():
    """Tests that an empty string is returned when no context is provided."""
    generator = MockLlmAnswerGenerator(context=None)
    assert generator._get_context_content() == ""


def test_get_context_content_string_context():
    """Tests that the string content is returned when context is a string."""
    test_string_context = "This is a test string context."
    generator = MockLlmAnswerGenerator(context=test_string_context)
    assert generator._get_context_content() == test_string_context


def test_get_context_content_file_exists(tmp_path):
    """Tests that content is read correctly from an existing file."""
    temp_file = tmp_path / "existing_context_file.txt"
    file_content = "Content of the existing file."
    temp_file.write_text(file_content)

    generator = MockLlmAnswerGenerator(context=temp_file)
    assert generator._get_context_content() == file_content
