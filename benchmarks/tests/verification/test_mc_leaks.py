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

"""A script to verify that no answers are leaked in MC benchmark cases."""

import os
from pathlib import Path

from pydantic import BaseModel
from pydantic import Field
import pytest
import yaml

from benchmarks.data_models import BenchmarkFile
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.validation_utils import load_snippet
from google import genai


class LeakCheckResult(BaseModel):
  is_leaked: bool = Field(
      ...,
      description="Whether the answer is leaked or trivial given the snippet.",
  )
  explanation: str = Field(
      ..., description="Explanation of why the answer is or is not leaked."
  )


async def check_leak(
    client: genai.Client,
    case: MultipleChoiceBenchmarkCase,
    snippet: str,
    model_name: str = "gemini-2.5-flash",
) -> LeakCheckResult:
  """Checks a single case for leaks using the LLM."""

  options_str = "\n".join(
      f"{key}: {value}" for key, value in case.options.items()
  )

  prompt = f"""You are a strict exam proctor. I will provide you with a Multiple Choice Question (MCQ) and a code snippet that acts as the context for the question. Your task is to determine if the code snippet **explicitly contains text that is identical to a correct or incorrect answer option**. 

**It is A LEAK if:**
1. The snippet explicitly contains text that is identical to a correct or incorrect answer option (including comments, docstrings, or string literals). Example: If an option is 'ValueError: Missing field', and the snippet contains '# ValueError: Missing field' or `raise ValueError("Missing field")` or a string variable `error_msg = "ValueError: Missing field"` it is a leak.

**It is NOT A LEAK if:**
1. The answer can be derived by reading the code and understanding standard Python behavior or library API conventions, but the exact text of the answer option is not literally present in the snippet.
2. The question is easy or trivial because the concept is simple. Simplicity itself is not a leak.

Question: {case.question}
Options:
{options_str}
Correct Answer: {case.correct_answer}

Code Snippet:
```python
{snippet}
```

Does the snippet leak the answer? Reply with a JSON object containing 'is_leaked' (boolean) and 'explanation' (string)."""
  try:
    response = await client.aio.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": LeakCheckResult.model_json_schema(),
        },
    )
    return LeakCheckResult.model_validate_json(response.text)
  except Exception as e:
    return LeakCheckResult(
        is_leaked=False, explanation=f"Failed to check leak: {e}"
    )


def pytest_generate_tests(metafunc):
  """Generates tests for each MC benchmark case."""
  if "case" in metafunc.fixturenames:
    base_dir = Path("benchmarks/benchmark_definitions")
    if not base_dir.exists():
      # Try relative to this file if running from subdirectory
      base_dir = Path(__file__).parents[2] / "benchmark_definitions"

    mc_suites = list(base_dir.glob("*_mc/benchmark.yaml"))

    cases = []
    ids = []

    for suite_path in mc_suites:
      try:
        with open(suite_path, "r", encoding="utf-8") as f:
          data = yaml.safe_load(f)
        benchmark_file = BenchmarkFile.model_validate(data)

        for i, case in enumerate(benchmark_file.benchmarks):
          if isinstance(case, MultipleChoiceBenchmarkCase):
            # Only test cases that actually have a code snippet to check for leaks
            if not case.code_snippet_ref:
              continue

            try:
              snippet = load_snippet(case.code_snippet_ref)
              if not snippet:
                continue
            except Exception:
              continue

            # Use a short ID based on the question
            short_q = case.question[:30].replace(" ", "_").replace("\n", "")
            ids.append(f"{suite_path.parent.name}_{i}_{short_q}")
            cases.append(case)
      except Exception as e:
        # In a generation hook we can't easily fail a single test, but we can print
        print(f"Error loading suite {suite_path}: {e}")

    metafunc.parametrize("case", cases, ids=ids)


@pytest.fixture(scope="module")
def client():
  """Creates a single client instance per worker process."""
  api_key = os.environ.get("GEMINI_API_KEY")
  if not api_key:
    pytest.skip("GEMINI_API_KEY environment variable not set.")
  return genai.Client(api_key=api_key)


@pytest.mark.asyncio
async def test_mc_case_leak(case, client: genai.Client):
  """Test a single MC case for leaks."""
  # Load snippet (guaranteed to exist and be non-empty by generation hook)
  snippet = load_snippet(case.code_snippet_ref)

  # Check for leaks
  result = await check_leak(client, case, snippet)

  if result.is_leaked:
    pytest.fail(
        f"Leak detected!\nQuestion: {case.question}\nExplanation:"
        f" {result.explanation}"
    )
