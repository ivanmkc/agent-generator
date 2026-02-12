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
Primary unified integration test suite for all Answer Generator implementations.
Also acts as the orchestration script for sequential generator execution.
"""

import sys
import os
from pathlib import Path
import datetime
import uuid

# Ensure project root is in sys.path for direct execution
project_root = Path(os.getcwd()).resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

import pytest
import json
import re
import asyncio
from colorama import init, Fore, Style
from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.validation_utils import validate_trace_log_expectations
from benchmarks.data_models import TraceLogEvent, TraceEventType

# Initialize colorama
init()

# Import for type hinting; pytest automatically finds fixtures in conftest
from benchmarks.tests.integration.conftest import GeneratorTestCase

# Imports for Orchestrator Logic
try:
    from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (
        GeminiCliPodmanAnswerGenerator,
    )
    from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
        IMAGE_DEFINITIONS,
    )
except ImportError:
    # Allow running purely as a test file without these imports if needed (e.g. unit testing setup)
    pass


                last_exception = e
                print(f"[{test_case.id}] Generation attempt {attempt + 1} failed: {e}. Retrying...")
                import asyncio
                await asyncio.sleep(1)

        if not answer:
            pytest.fail(f"[{test_case.id}] Generation failed after 3 attempts. Last error: {last_exception}")


        # Basic Checks
        assert answer is not None
        assert answer.output is not None

        # Verify output type matches the benchmark case type using the case's validation method
        try:
            case.validate_answer_format(answer.output)
        except AssertionError as e:
            pytest.fail(f"Answer validation failed: {e}")

        # Trace Log Checks
        if answer.trace_logs:
            logs_str = json.dumps(
                [t.model_dump() for t in answer.trace_logs], default=str
            )
            project_tmp_dir = Path("tmp/test_traces")
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = (
                project_tmp_dir / f"{test_case.id}_{timestamp_str}_debug_trace.json"
            )
            log_file.parent.mkdir(
                parents=True, exist_ok=True
            )  # Ensure directory exists
            with open(log_file, "w") as f:
                f.write(logs_str)
            print(
                f"{Fore.GREEN}[{test_case.id}] Debug traces saved to {log_file}{Style.RESET_ALL}"
            )

            # Validate trace log expectations (Tools & Sub-Agents)
            success, error_msg = validate_trace_log_expectations(
                answer.trace_logs,
                test_case.expected_sub_agent_calls,
                test_case.expected_tool_uses,
            )

            if not success:
                pytest.fail(f"[{test_case.id}] Trace validation failed: {error_msg}")

        else:
            print(f"[{test_case.id}] Warning: No trace logs returned.")

    except Exception as e:
        pytest.fail(f"[{test_case.id}] Generation failed: {e}")


        pytest.fail(f"[{test_case.id}] Failed to run debug command: {e}")

    # Combine all log content for easier searching
    full_logs_content = "\n".join([event.content for event in logs if event.content])
    # print(f"[{test_case.id}] Full debug logs (snippet):\n{full_logs_content[:1000]}...")

    # Regex to find all "Final ordered ... paths to read" lines
    # Example: [DEBUG] [MemoryDiscovery] Final ordered adk_skill/instructions.md paths to read: ["/workdir/adk_skill/instructions.md"]
    loaded_paths = []
    path_matches = re.findall(
        r"\[DEBUG\] \[MemoryDiscovery\] Final ordered .*? paths to read: (.*)",
        full_logs_content,
    )

    if not path_matches:
        pytest.fail(
            f"[{test_case.id}] No 'Final ordered ... paths' debug lines found in logs."
        )

    for paths_str in path_matches:
        try:
             # Replace single quotes with double for valid JSON if needed (though CLI usually outputs valid JSON)
            clean_json = paths_str.replace("'", '"')
            batch_paths = json.loads(clean_json)
            loaded_paths.extend(batch_paths)
        except json.JSONDecodeError:
            print(f"[{test_case.id}] Warning: Could not parse paths JSON: {paths_str}")
            continue

    print(f"[{test_case.id}] Discovered loaded context paths: {loaded_paths}")

    # Assert that all expected files are present in the loaded paths
    for expected_file in test_case.expected_context_files:
        assert (
            expected_file in loaded_paths
        ), f"Expected context file '{expected_file}' not found in loaded memory paths. Available: {loaded_paths}"


            print(f"!!! [{gen_id}] Initialization FAILED: {e}")
            continue

        try:
            print(f"[{gen_id}] Setting up...")
            await generator.setup()

            # Get URL (standardize access)
            service_url = getattr(generator, "_base_url", None) or getattr(
                generator, "service_url", None
            )

            if not service_url:
                raise RuntimeError(
                    f"Generator {gen_id} failed to return a service URL after setup."
                )

            print(f"[{gen_id}] Service active at {service_url}")

            # Prepare Environment for Pytest
            env = os.environ.copy()
            env["TEST_GENERATOR_ID"] = gen_id
            env["TEST_GENERATOR_URL"] = service_url

            # Run Pytest for this specific case
            print(f"[{gen_id}] Launching pytest with -n auto...")

            # Point to THIS file
            test_file = __file__

            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "-n",
                "auto",
                "-rs",
                "-s",
                "-v",
                "--profile",
                "--import-mode=importlib",
                # Filter strictly for this test case parameter
                "-k",
                gen_id,
                test_file,
            ]

            proc = await asyncio.create_subprocess_exec(*cmd, env=env)
            await proc.wait()

            if proc.returncode != 0:
                print(f"!!! [{gen_id}] Tests FAILED with code {proc.returncode}")
            else:
                print(f"[{gen_id}] Tests PASSED")

        except Exception as e:
            print(f"!!! [{gen_id}] Error during execution: {e}")

        finally:
            print(f"[{gen_id}] Tearing down...")
            if generator:
                await generator.teardown()

    print("\n=== Suite Complete ===")


if __name__ == "__main__":
    asyncio.run(run_orchestrator())
