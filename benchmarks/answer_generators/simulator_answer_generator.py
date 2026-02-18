import sys
from pathlib import Path

# Add tools/simulator to sys.path
project_root = Path(__file__).parent.parent.parent
simulator_path = project_root / 'tools'
sys.path.insert(0, str(simulator_path))

from simulator.runner import SimulationRunner
from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.data_models import BenchmarkCase, GeneratedAnswer, SimulatorAnswerOutput, SimulatorBenchmarkCase, UsageMetadata
from core.api_key_manager import ApiKeyManager

class SimulatorAnswerGenerator(AnswerGenerator):
    def __init__(self, backend: str, api_key_manager: ApiKeyManager):
        self.backend = backend
        self.api_key_manager = api_key_manager

    @property
    def name(self) -> str:
        return f"SimulatorAnswerGenerator(backend={self.backend})"

    async def generate_answer(self, benchmark_case: BenchmarkCase, retries: int = 3) -> GeneratedAnswer:
        if not isinstance(benchmark_case, SimulatorBenchmarkCase):
            raise TypeError(f"Expected SimulatorBenchmarkCase, got {type(benchmark_case)}")

        runner = SimulationRunner(
            case=benchmark_case.simulation_case, 
            backend_command=self.backend,
            api_key_manager=self.api_key_manager
        )
        
        result = await runner.run_async()

        return GeneratedAnswer(
            output=SimulatorAnswerOutput(
                rationale="Simulation completed.",
                transcript=result.transcript,
                is_correct=result.success,
                benchmark_type="simulator",
            ),
            trace_logs=result.trace_logs,
            usage_metadata=UsageMetadata() # Placeholder
        )
