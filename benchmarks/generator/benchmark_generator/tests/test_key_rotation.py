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

"""Tests for API key rotation logic in SemaphoreGemini."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from benchmarks.generator.benchmark_generator.agents import SemaphoreGemini
from benchmarks.api_key_manager import ApiKeyManager


@pytest.mark.asyncio
async def test_key_rotation_on_429():
    """
    Verifies that SemaphoreGemini retries on 429 errors.
    Since SemaphoreGemini inherits from RotatingKeyGemini, and RotatingKeyGemini
    selects a key on each client access (which happens inside generate_content_async),
    a retry effectively rotates the key.
    """
    sem = asyncio.Semaphore(1)
    akm = MagicMock(spec=ApiKeyManager)

    # Patch the superclass method to simulate failure then success
    # We patch the method on the CLASS RotatingKeyGemini where it is defined
    with patch(
        "benchmarks.answer_generators.adk_agents.RotatingKeyGemini.generate_content_async",
        new_callable=AsyncMock,
    ) as mock_super:
        # Define side effects:
        # 1. Raise 429 Error
        # 2. Return "Success" (as a simple value, wrapper yields it)
        error_429 = Exception("429 RESOURCE_EXHAUSTED")
        mock_super.side_effect = [error_429, "Success"]

        # Instantiate model
        model = SemaphoreGemini(semaphore=sem, api_key_manager=akm, model_name="test")

        # Execute
        # generate_content_async returns an async generator wrapper
        agen = model.generate_content_async("prompt")

        results = []
        async for res in agen:
            results.append(res)

        # Verify results
        assert results == ["Success"]

        # Verify retries
        assert mock_super.call_count == 2
