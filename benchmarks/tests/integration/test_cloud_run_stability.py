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

"""
Stability and stress tests for Cloud Run deployed Answer Generators.

This test file verifies the resilience and error handling of generators running on
Google Cloud Run under high concurrency. It checks for:
- Successful service deployment and connectivity.
- Handling of concurrent requests up to defined limits.
- Proper error reporting during failures.

Prerequisites:
- Valid Google Cloud credentials.
- 'gemini-api-key' secret in Secret Manager.
"""

import asyncio
import os
from pathlib import Path
import pytest
from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator import (
    GeminiCliCloudRunAnswerGenerator,
)
from benchmarks.config import CLOUD_RUN_CONFIG
from benchmarks.data_models import FixErrorBenchmarkCase, BenchmarkType

# This test requires authentication and a deployed Cloud Run service.
# It uses the adk-gemini-sandbox service by default.
# Note: The service requires 'gemini-api-key' secret in Secret Manager for API Key auth.

@pytest.mark.asyncio
async def test_cloud_run_stability():
    # Configuration
    SERVICE_NAME = "adk-gemini-sandbox"
    DOCKERFILE_DIR = "benchmarks/answer_generators/gemini_cli_docker/adk-python" 
    MODEL = "gemini-2.5-flash"
    CONCURRENCY = CLOUD_RUN_CONFIG.MAX_GLOBAL_CONCURRENCY  # Should be 400 now (Horizontal Scaling Test)
    
    # Check if we have credentials
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and not os.environ.get("GOOGLE_CLOUD_PROJECT"):
         try:
             import google.auth
             _, project = google.auth.default()
             if not project:
                 pytest.skip("No Google Cloud credentials found.")
         except:
             pytest.skip("No Google Cloud credentials found.")

    generator = GeminiCliCloudRunAnswerGenerator(
        service_name=SERVICE_NAME,
        dockerfile_dir=DOCKERFILE_DIR,
        model_name=MODEL,
        auto_deploy=True, 
        force_deploy=True # Force update of configuration (resources/concurrency)
    )
    
    print(f"Setting up generator for service {SERVICE_NAME}...")
    try:
        await generator.setup()
    except Exception as e:
        if "billing account" in str(e) or "403" in str(e):
             pytest.skip(f"Skipping stability test due to billing/permissions error: {e}")
        raise

    if not generator.service_url:
        pytest.fail(f"Could not resolve URL for service {SERVICE_NAME}. Is it deployed?")
        
    print(f"Targeting Service: {generator.service_url}")
    
    # Define a real ADK case
    case_dir = Path("benchmarks/benchmark_definitions/fix_errors/cases/01_single_llm_agent")
    if not case_dir.exists():
        pytest.fail(f"Case directory not found: {case_dir}")

    case = FixErrorBenchmarkCase(
        name="Stress Test Case",
        description="Create a minimal LlmAgent named 'root_agent' that can use the `basic_tool`.",
        test_file=case_dir / "test_agent.py",
        unfixed_file=case_dir / "unfixed.py",
        requirements=[
            "The generated solution must be a complete Python file defining a function `create_agent(model_name: str) -> BaseAgent:`.",
            "When asked 'Can you use your tool?', the agent should use the `basic_tool`."
        ],
    )
    
    print(f"Sending {CONCURRENCY} concurrent generate_answer requests...")
    
    tasks = []
    for i in range(CONCURRENCY):
        tasks.append(generator.generate_answer(case))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    failures = 0
    errors = []
    for r in results:
        if isinstance(r, Exception):
            failures += 1
            errors.append(str(r))
            
    if failures > 0:
        print(f"--- FAILURES ({failures}/{CONCURRENCY}) ---")
        for e in errors[:5]: # Print first 5 unique
            print(f"  - {e}")
    
    assert failures == 0, f"{failures} requests failed out of {CONCURRENCY}. Errors: {errors[:3]}"
