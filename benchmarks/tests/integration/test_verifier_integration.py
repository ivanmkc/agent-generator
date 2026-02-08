import asyncio
import pytest
from pathlib import Path
import json
import shutil
from tools.verify_benchmarks import verify_benchmark
from core.api_key_manager import ApiKeyManager
from core.config import DATA_DIR, MOST_POWERFUL_MODEL

@pytest.mark.asyncio
async def test_verifier_end_to_end():
    """
    Integration test for the Quality Verifier.
    Tests the pipeline on a known valid case.
    """
    benchmark_file = Path("benchmarks/benchmark_definitions/verification_test_mc/benchmark.yaml")
    output_dir = DATA_DIR / "test_verification_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    api_key_manager = ApiKeyManager()
    
    # Use the most powerful model for verification reliability
    model = MOST_POWERFUL_MODEL
    
    print(f"\nStarting integration test with model: {model}")
    
    results = await verify_benchmark(
        benchmark_file=benchmark_file,
        run_dir=output_dir,
        model_name=model,
        api_key_manager=api_key_manager
    )
    
    assert results is not None
    assert len(results) == 1
    
    case_result = results[0]
    assert case_result["id"] == "verification_test_mc:agent_init"
    
    # The verdict should be Valid because the question is factually correct
    # A is 'name' (correct), B is 'agent_id' (incorrect)
    print(f"Integration Test Verdict: {case_result['verdict']}")
    
    # We allow 'Unknown' or 'Error' only if the model failed to respond or quota hit,
    # but for a successful test, we expect 'Valid'.
    # If it returns 'Incorrect' or 'Ambiguous', the verifier actually found a flaw 
    # (or the verifier itself is flawed).
    assert case_result["verdict"] == "Valid"
    
    # Cleanup
    if output_dir.exists():
        shutil.rmtree(output_dir)

if __name__ == "__main__":
    asyncio.run(test_verifier_end_to_end())
