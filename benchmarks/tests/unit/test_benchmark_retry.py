
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import pydantic
from benchmarks.benchmark_orchestrator import run_benchmarks
from benchmarks.answer_generators import AnswerGenerator
from benchmarks.data_models import BaseBenchmarkCase, GeneratedAnswer, BenchmarkType, TraceLogEvent
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks import benchmark_orchestrator

class MockBenchmarkCase(BaseBenchmarkCase):
    def get_identifier(self) -> str:
        return "mock_case"
    
    @property
    def runner(self):
        runner = AsyncMock()
        runner.run_benchmark.return_value = ("fail", "Validation failed", None, None)
        return runner

    def validate_answer_format(self, output):
        pass

    def get_ground_truth(self):
        return "ground_truth"

    def get_unfixed_code(self):
        return "unfixed_code"

class MockAnswerGenerator(AnswerGenerator):
    def __init__(self, name="mock_generator"):
        super().__init__()
        self._name = name
        self.call_count = 0
        self.api_key_manager = MagicMock(spec=ApiKeyManager)

    @property
    def name(self) -> str:
        return self._name

    async def generate_answer(self, benchmark_case, run_id):
        self.call_count += 1
        # Create a real pydantic ValidationError
        class MyModel(pydantic.BaseModel):
            foo: int
        
        try:
            MyModel(foo="bar")
        except pydantic.ValidationError as e:
            # Wrap in BenchmarkGenerationError as done in AdkAnswerGenerator
            from benchmarks.data_models import BenchmarkGenerationError
            raise BenchmarkGenerationError("Validation failed", original_exception=e) from e

class TestBenchmarkRetry(unittest.IsolatedAsyncioTestCase):
    
    async def test_no_retry_on_validation_error(self):
        generator = MockAnswerGenerator()
        case = MockBenchmarkCase(id="test:retry", benchmark_type=BenchmarkType.FIX_ERROR)
        
        # We need to mock loading the suite file, so we'll mock yaml.safe_load and open
        with (
            patch("builtins.open", unittest.mock.mock_open(read_data="benchmarks: []")),
            patch("yaml.safe_load", return_value={"benchmarks": []}) as mock_yaml
        ):
            
            # Since we can't easily inject the case via yaml load in run_benchmarks without more complex mocking,
            # let's call _run_single_benchmark directly or just mock the file parsing part.
            # Actually, calling _run_single_benchmark is easier and tests the core logic.
            
            semaphore = asyncio.Semaphore(1)
            result = await benchmark_orchestrator._run_single_benchmark(
                suite_file="mock_suite.yaml",
                case=case,
                generator=generator,
                semaphore=semaphore,
                logger=None,
                max_retries=2,
                min_wait=0.01,
                max_wait=0.01,
                retry_on_validation_error=False
            )
            
            # Should fail after 1 attempt because validation error occurred and retry is False
            self.assertEqual(generator.call_count, 1)
            self.assertEqual(result.status, "fail_generation")

    async def test_retry_on_validation_error(self):
        generator = MockAnswerGenerator()
        case = MockBenchmarkCase(id="test:retry", benchmark_type=BenchmarkType.FIX_ERROR)
        
        semaphore = asyncio.Semaphore(1)
        result = await benchmark_orchestrator._run_single_benchmark(
            suite_file="mock_suite.yaml",
            case=case,
            generator=generator,
            semaphore=semaphore,
            logger=None,
            max_retries=2,
            min_wait=0.01,
            max_wait=0.01,
            retry_on_validation_error=True
        )
        
        # Should fail after 3 attempts (1 initial + 2 retries)
        self.assertEqual(generator.call_count, 3)
        self.assertEqual(result.status, "fail_generation")

if __name__ == '__main__':
    unittest.main()
