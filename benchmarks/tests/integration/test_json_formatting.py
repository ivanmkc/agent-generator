import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.benchmark_runner import MultipleChoiceRunner
from benchmarks.data_models import MultipleChoiceBenchmarkCase, BenchmarkType, GeneratedAnswer, MultipleChoiceAnswerOutput
from benchmarks.api_key_manager import ApiKeyManager

@pytest.mark.asyncio
async def test_json_sanitizer_integration(monkeypatch):
    # 1. Setup Mock Generator that returns bad JSON
    mock_agent = MagicMock()
    mock_agent.name = "BadJsonAgent"
    
    # Mock ApiKeyManager
    mock_api = MagicMock()
    mock_api.get_key_for_run = AsyncMock(return_value=("fake_key", "1"))
    mock_api.report_result = AsyncMock()
    mock_api.get_next_key = AsyncMock(return_value="fake_key_sanitizer")
    
    # Mock global API_KEY_MANAGER used by runner
    monkeypatch.setattr("benchmarks.api_key_manager.API_KEY_MANAGER", mock_api)
    
    generator = AdkAnswerGenerator(agent=mock_agent, api_key_manager=mock_api)
    
    # Mock _run_agent_async to return bad JSON text
    bad_text = "Here is the answer: {'answer': 'B', 'rationale': 'Because.'} (oops invalid quotes)"
    generator._run_agent_async = AsyncMock(return_value=(bad_text, [], None, "session_1"))
    
    # 2. Setup Benchmark Case
    case = MultipleChoiceBenchmarkCase(
        id="test:bad_json",
        question="What is 1+1?",
        options={"A": "1", "B": "2"},
        correct_answer="B",
        benchmark_type=BenchmarkType.MULTIPLE_CHOICE
    )
    
    # 3. Setup Runner
    runner = MultipleChoiceRunner()
    
    # 4. Mock Sanitizer Client to simulate LLM repair
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"answer": "B", "rationale": "Because.", "benchmark_type": "multiple_choice"}'
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    
    monkeypatch.setattr("benchmarks.parsing.json_sanitizer.Client", MagicMock(return_value=mock_client))

    # 5. Run Generation
    answer = await generator.generate_answer(case, run_id="test_run")
    
    # Verify Generator returned raw_output because parse failed
    assert answer.output is None
    assert answer.raw_output == bad_text
    
    # 6. Run Runner (Validation Phase)
    result, log, _, _ = await runner.run_benchmark(case, answer)
    
    # 7. Assertions
    assert result == "pass"
    assert answer.output is not None # Should be patched
    assert answer.output.answer == "B"
    
    # Verify Sanitizer was called via Client
    mock_client.aio.models.generate_content.assert_called()
