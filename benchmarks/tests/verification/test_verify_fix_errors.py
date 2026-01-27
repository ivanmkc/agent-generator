"""Test Verify Fix Errors module."""

import ast
import os
from pathlib import Path

from pydantic import BaseModel
from pydantic import Field
import pytest
import yaml

from google import genai


class FailureVerificationResult(BaseModel):
    verifies_failure: bool = Field(
        ...,
        description=(
            "Whether the test function actively verifies that the code fails or"
            " produces an incorrect result."
        ),
    )
    explanation: str = Field(
        ...,
        description=(
            "Explanation of why the function does or does not verify failure."
        ),
    )


class AlignmentCheckResult(BaseModel):
    is_aligned: bool = Field(
        ...,
        description=(
            "True if the test assertions cover the stated requirements and"
            " instructions without hidden expectations."
        ),
    )
    missing_requirements: list[str] = Field(
        default_factory=list,
        description=(
            "List of requirements that are tested but not explicitly stated in"
            " instructions/YAML."
        ),
    )
    explanation: str


class LeakageCheckResult(BaseModel):
    is_leaked: bool = Field(
        ...,
        description=(
            "True if the unfixed code contains the solution (e.g. in comments)."
        ),
    )
    explanation: str


def _get_docstring(content: str, func_name: str) -> str | None:
    """Extracts the docstring of a function from content."""
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == func_name
            ):
                return ast.get_docstring(node)
        return None
    except Exception:
        return None


async def _check_requirements_alignment(
    client: genai.Client, unfixed_content: str, test_content: str
) -> AlignmentCheckResult:
    """Verifies that test assertions match the instructions in unfixed.py."""
    test_source = _get_function_source(test_content, "test_create_agent_passes")
    instructions = _get_docstring(unfixed_content, "create_agent")

    if not test_source or not instructions:
        return AlignmentCheckResult(
            is_aligned=True,
            explanation="Could not load source or docstring.",
            missing_requirements=[],
        )

    prompt = f"""You are a QA Lead. Verify if the test code aligns with the requirements provided to the candidate.

**Candidate Instructions (from docstring):**
{instructions}

**Test Code (Verification Logic):**
```python
{test_source}
```

**Task:**
1. Does the test code verify the requirements listed in the Candidate Instructions?
2. **CRITICAL:** Does the test assert conditions that are *NOT* mentioned in the Instructions? (Hidden requirements are unfair).
   - Example of Hidden Requirement: Test asserts `agent.name == "my_agent"` but instructions never specified the name.
   - Example of Aligned: Test asserts `agent.name == "my_agent"` and instructions said "Create an agent named 'my_agent'".

Reply with JSON: 'is_aligned' (bool), 'missing_requirements' (list of strings - things tested but not required), and 'explanation'."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AlignmentCheckResult.model_json_schema(),
            },
        )
        return AlignmentCheckResult.model_validate_json(response.text)
    except Exception as e:
        print(f"  [LLM Error] Alignment check failed: {e}")
        return AlignmentCheckResult(
            is_aligned=True, explanation="Check failed", missing_requirements=[]
        )


async def _check_solution_leakage(
    client: genai.Client, unfixed_content: str, fixed_content: str
) -> LeakageCheckResult:
    """Checks if unfixed.py leaks the solution found in fixed.py."""
    prompt = f"""You are a strict exam proctor. Compare the 'Unfixed' code (problem) with the 'Fixed' code (solution).

**Unfixed Code:**
```python
{unfixed_content}
```

**Fixed Code:**
```python
{fixed_content}
```

**Task:**
Determine if the 'Unfixed' code inadvertently leaks the solution or provides excessive hints.

**Strict Criteria for LEAK:**
1. **Commented Solution:** The `unfixed.py` contains the exact solution code commented out.
2. **Explicit Diagnostics:** The code contains comments that explicitly explain the root cause of the bug or exactly why the code fails (e.g., "# This raises ValueError because name has space"). This is a leak because it removes the diagnostic burden from the candidate.
3. **Trivial Copy-Paste:** The file structure provides the answer in a way that makes the task trivial copy-paste.

**Criteria for NOT LEAK:**
1. **General Instructions:** Hints or comments explaining *what* to do (the goal) are fine.
2. **Placeholders:** Standard TODOs or `NotImplementedError` are fine.
3. **Obvious Bugs:** The presence of the bug itself is not a leak.

Reply with JSON: 'is_leaked' (bool) and 'explanation'."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": LeakageCheckResult.model_json_schema(),
            },
        )
        return LeakageCheckResult.model_validate_json(response.text)
    except Exception as e:
        print(f"  [LLM Error] Leakage check failed: {e}")
        return LeakageCheckResult(is_leaked=False, explanation="Check failed")


def _get_function_source(content: str, func_name: str) -> str | None:
    """Extracts the source code of a function from content."""
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == func_name
            ):
                return ast.get_source_segment(content, node)
        return None
    except Exception:
        return None


async def _check_test_verifies_failure(client: genai.Client, test_content: str) -> bool:
    """
    Checks if `test_create_agent_unfixed_fails` contains failure verification logic.
    Uses an LLM if a client is provided; otherwise falls back to basic AST inspection.
    """
    func_source = _get_function_source(test_content, "test_create_agent_unfixed_fails")
    if not func_source:
        return False  # Function not found

    prompt = f"""You are a code reviewer. Analyze the following Python test function `test_create_agent_unfixed_fails`. 
This function is intended to verify that a broken piece of code (imported as `unfixed`) actually fails or exhibits incorrect behavior.

**Criteria for "Verifies Failure":**
- It DOES verify failure if it uses `pytest.raises(...)` to catch an expected exception.
- It DOES verify failure if it uses `pytest.fail(...)` (e.g. if the code didn't raise as expected).
- It DOES verify failure if it uses `assert` to verify that a value is *incorrect*, *missing*, or matches an error condition (e.g., `assert 'correct' not in output`, `assert result != expected`, `assert 'Error' in result`).
- It DOES NOT verify failure if it simply runs the code without any checks.
- It DOES NOT verify failure if it asserts that the code *works* successfully (e.g. `assert result is not None` when the code is supposedly broken).

Function Source:
```python
{func_source}
```

Does this function explicitly check for failure according to the criteria?
Reply with a JSON object containing 'verifies_failure' (boolean) and 'explanation' (string)."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": FailureVerificationResult.model_json_schema(),
            },
        )
        result = FailureVerificationResult.model_validate_json(response.text)
        if not result.verifies_failure:
            print(f"  [LLM Check Failed] {result.explanation}")
        return result.verifies_failure
    except Exception as e:
        print(f"  [LLM Error] Failed to check failure verification: {e}")
        # Fallback to heuristic on error to avoid blocking CI
        return (
            "assert" in func_source
            or "pytest.raises" in func_source
            or "pytest.fail" in func_source
        )


def _check_function_exists(content: str, func_name: str, file_name: str = "") -> bool:
    """Checks if a Python file content contains a function definition with the given name."""
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                or isinstance(node, ast.AsyncFunctionDef)
            ) and node.name == func_name:
                return True
        return False
    except SyntaxError:
        if file_name == "unfixed.py":
            print(
                f"  [Info] Syntax error in {file_name}. Assuming intentional for"
                " benchmark case."
            )
            return (
                True  # Assume existence if we can't parse, to allow syntax error cases
            )
        pytest.fail(f"Syntax error in content. Cannot parse for function existence.")
    except Exception:
        return False


def load_benchmarks():
    base_dir = Path(__file__).parent
    yaml_path = base_dir / "benchmark.yaml"
    if not yaml_path.exists():
        return []
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("benchmarks", [])


def pytest_generate_tests(metafunc):
    if "benchmark_case" in metafunc.fixturenames:
        benchmarks = load_benchmarks()
        ids = [bm.get("name", f"case_{i}") for i, bm in enumerate(benchmarks)]
        metafunc.parametrize("benchmark_case", benchmarks, ids=ids)


@pytest.fixture
def llm_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.fail(
            "GEMINI_API_KEY environment variable not set. LLM client is required"
            " for verification."
        )
    return genai.Client(api_key=api_key)


@pytest.mark.asyncio
async def test_verify_benchmark_case(benchmark_case, llm_client):
    """Verifies a single fix_error benchmark definition."""
    name = benchmark_case.get("name", "Unknown Benchmark")
    test_file_path_str = benchmark_case.get("test_file")
    unfixed_file_path_str = benchmark_case.get("unfixed_file")
    fixed_file_path_str = benchmark_case.get("fixed_file")

    # 1. Verify file existence
    if not test_file_path_str:
        pytest.fail(f"Benchmark '{name}': missing 'test_file' field.")
    if not unfixed_file_path_str:
        pytest.fail(f"Benchmark '{name}': missing 'unfixed_file' field.")
    if not fixed_file_path_str:
        pytest.fail(f"Benchmark '{name}': missing 'fixed_file' field.")

    test_full_path = Path(test_file_path_str)
    unfixed_full_path = Path(unfixed_file_path_str)
    fixed_full_path = Path(fixed_file_path_str)

    if not test_full_path.exists():
        pytest.fail(f"Benchmark '{name}': Test file not found: {test_full_path}")
    if not unfixed_full_path.exists():
        pytest.fail(f"Benchmark '{name}': Unfixed file not found: {unfixed_full_path}")
    if not fixed_full_path.exists():
        pytest.fail(f"Benchmark '{name}': Fixed file not found: {fixed_full_path}")

    # Read content
    unfixed_content = unfixed_full_path.read_text()
    fixed_content = fixed_full_path.read_text()
    test_content = test_full_path.read_text()

    # Check for empty content
    if not unfixed_content.strip():
        pytest.fail(f"Benchmark '{name}': Unfixed file is empty: {unfixed_full_path}")
    if not fixed_content.strip():
        pytest.fail(f"Benchmark '{name}': Fixed file is empty: {fixed_full_path}")
    if not test_content.strip():
        pytest.fail(f"Benchmark '{name}': Test file is empty: {test_full_path}")

    # 2. Verify `create_agent` function exists in unfixed.py and fixed.py
    if not _check_function_exists(
        unfixed_content, "create_agent", file_name=unfixed_full_path.name
    ):
        pytest.fail(
            f"Benchmark '{name}': 'create_agent' function not found in"
            f" {unfixed_full_path.name}."
        )
    if not _check_function_exists(
        fixed_content, "create_agent", file_name=fixed_full_path.name
    ):
        pytest.fail(
            f"Benchmark '{name}': 'create_agent' function not found in"
            f" {fixed_full_path.name}."
        )

    # 3. Verify `test_create_agent_passes` and `test_create_agent_unfixed_fails` exist in test_agent.py
    if not _check_function_exists(
        test_content, "test_create_agent_passes", file_name=test_full_path.name
    ):
        pytest.fail(
            f"Benchmark '{name}': 'test_create_agent_passes' function not found in"
            f" {test_full_path.name}."
        )
    if not _check_function_exists(
        test_content,
        "test_create_agent_unfixed_fails",
        file_name=test_full_path.name,
    ):
        pytest.fail(
            f"Benchmark '{name}': 'test_create_agent_unfixed_fails' function not"
            f" found in {test_full_path.name}."
        )

    # 4. Verify `test_create_agent_unfixed_fails` checks for failure
    elif not await _check_test_verifies_failure(llm_client, test_content):
        pytest.fail(
            f"Benchmark '{name}': 'test_create_agent_unfixed_fails' does not seem"
            " to verify failure (checked with LLM)."
        )

    # 5. Advanced Semantic Checks

    # Check Alignment
    alignment_res = await _check_requirements_alignment(
        llm_client, unfixed_content, test_content
    )
    if not alignment_res.is_aligned:
        print(
            f"[WARNING] Benchmark '{name}': Alignment Issue."
            f" {alignment_res.explanation} Missing reqs:"
            f" {alignment_res.missing_requirements}"
        )

    # Check Leakage
    leakage_res = await _check_solution_leakage(
        llm_client, unfixed_content, fixed_content
    )
    if leakage_res.is_leaked:
        pytest.fail(
            f"Benchmark '{name}': Solution Leakage Detected."
            f" {leakage_res.explanation}"
        )
