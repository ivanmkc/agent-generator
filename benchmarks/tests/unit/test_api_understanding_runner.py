"""Test Api Understanding Runner module."""

import sys
import pytest
from pathlib import Path
from benchmarks.benchmark_runner import ApiUnderstandingRunner
from benchmarks.data_models import (
    ApiUnderstandingBenchmarkCase,
    GeneratedAnswer,
    ApiUnderstandingAnswerOutput,
    StringMatchAnswer,
    BenchmarkResultType,
    AnswerTemplate,
)


@pytest.mark.asyncio
async def test_run_benchmark_handles_reexports(tmp_path):
    """
    Tests that ApiUnderstandingRunner correctly identifies valid re-exports
    where the generated path and expected path point to the same object ID.
    """
    # 1. Setup a temporary package with a re-export
    pkg_dir = tmp_path / "test_pkg_reexport"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()

    # internal.py defines the class
    (pkg_dir / "internal.py").write_text("class MyClass:\n    pass")

    # public.py re-exports it
    (pkg_dir / "public.py").write_text("from .internal import MyClass")

    # Add tmp_path to sys.path so we can import 'test_pkg_reexport'
    sys.path.insert(0, str(tmp_path))

    try:
        # 2. Construct the benchmark case
        # Expected path is the internal one
        case = ApiUnderstandingBenchmarkCase(
            id="test:reexport_success",
            benchmark_type="api_understanding",
            category="test",
            question="test",
            rationale="test",
            template=AnswerTemplate.CLASS_DEFINITION,
            answers=[
                StringMatchAnswer(
                    answer_template="StringMatchAnswer",
                    answer="MyClass",
                    fully_qualified_class_name=["test_pkg_reexport.internal.MyClass"],
                )
            ],
            file=Path("dummy.py"),
        )
        # 3. Construct the generated answer
        # Generated path is the public re-export
        generated_answer = GeneratedAnswer(
            output=ApiUnderstandingAnswerOutput(
                benchmark_type="api_understanding",
                rationale="test",
                code="MyClass",
                fully_qualified_class_name="test_pkg_reexport.public.MyClass",
            )
        )

        # 4. Run the benchmark
        runner = ApiUnderstandingRunner()
        result, logs, _, _ = await runner.run_benchmark(case, generated_answer)

        # 5. Assert Success
        assert (
            result == BenchmarkResultType.PASS
        ), f"Validation failed despite valid re-export. Logs: {logs}"

    finally:
        # Cleanup sys.path
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))


@pytest.mark.asyncio
async def test_run_benchmark_fails_on_different_objects(tmp_path):
    """
    Tests that ApiUnderstandingRunner fails when paths resolve to different objects.
    """
    pkg_dir = tmp_path / "test_pkg_diff"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()

    # Two different classes
    (pkg_dir / "a.py").write_text("class MyClass:\n    pass")
    (pkg_dir / "b.py").write_text("class MyClass:\n    pass")

    sys.path.insert(0, str(tmp_path))

    try:
        case = ApiUnderstandingBenchmarkCase(
            id="test:reexport_fail",
            benchmark_type="api_understanding",
            category="test",
            question="test",
            rationale="test",
            template=AnswerTemplate.CLASS_DEFINITION,
            answers=[
                StringMatchAnswer(
                    answer_template="StringMatchAnswer",
                    answer="MyClass",
                    fully_qualified_class_name=["test_pkg_diff.a.MyClass"],
                )
            ],
            file=Path("dummy.py"),
        )

        generated_answer = GeneratedAnswer(
            output=ApiUnderstandingAnswerOutput(
                benchmark_type="api_understanding",
                rationale="test",
                code="MyClass",
                fully_qualified_class_name="test_pkg_diff.b.MyClass",
            )
        )

        runner = ApiUnderstandingRunner()
        result, logs, _, _ = await runner.run_benchmark(case, generated_answer)

        assert result == BenchmarkResultType.FAIL_VALIDATION
        assert "does not exactly match" in logs or "Validation Failed" in logs

    finally:
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
