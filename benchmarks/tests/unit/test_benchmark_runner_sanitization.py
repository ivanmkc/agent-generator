import pytest
from unittest.mock import MagicMock, AsyncMock
from pydantic import BaseModel
from benchmarks.benchmark_runner import BenchmarkRunner
from benchmarks.data_models import GeneratedAnswer, FixErrorAnswerOutput, BenchmarkType

class MockRunner(BenchmarkRunner):
    async def run_benchmark(self, case, answer):
        pass

@pytest.mark.asyncio
async def test_ensure_valid_output_already_parsed():
    runner = MockRunner()
    output = FixErrorAnswerOutput(benchmark_type=BenchmarkType.FIX_ERROR, code="print('ok')", rationale="test")
    answer = GeneratedAnswer(output=output)
    
    out, err = await runner.ensure_valid_output(answer, FixErrorAnswerOutput)
    assert out.code == "print('ok')"
    assert err is None

@pytest.mark.asyncio
async def test_ensure_valid_output_sanitizes(monkeypatch):
    runner = MockRunner()
    answer = GeneratedAnswer(output=None, raw_output='{"code": "sanitized", "rationale": "r", "benchmark_type": "fix_error"}')
    
    mock_sanitizer_cls = MagicMock()
    mock_instance = MagicMock()
    
    expected_output = FixErrorAnswerOutput(benchmark_type=BenchmarkType.FIX_ERROR, code="sanitized", rationale="r")
    mock_instance.sanitize = AsyncMock(return_value=expected_output)
    mock_sanitizer_cls.return_value = mock_instance
    
    monkeypatch.setattr("benchmarks.parsing.json_sanitizer.JsonSanitizer", mock_sanitizer_cls)
    
    out, err = await runner.ensure_valid_output(answer, FixErrorAnswerOutput)
    assert out.code == "sanitized"
    assert err is None
    assert answer.output == out

@pytest.mark.asyncio
async def test_ensure_valid_output_fails(monkeypatch):
    runner = MockRunner()
    answer = GeneratedAnswer(output=None, raw_output="bad")
    
    mock_sanitizer_cls = MagicMock()
    mock_instance = MagicMock()
    mock_instance.sanitize = AsyncMock(side_effect=ValueError("Boom"))
    mock_sanitizer_cls.return_value = mock_instance
    
    monkeypatch.setattr("benchmarks.parsing.json_sanitizer.JsonSanitizer", mock_sanitizer_cls)
    
    out, err = await runner.ensure_valid_output(answer, FixErrorAnswerOutput)
    assert out is None
    assert "Boom" in err
