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

"""An AnswerGenerator that uses the local gemini CLI to generate answers."""

import asyncio
from typing import Any

from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.data_models import TraceLogEvent
from benchmarks.utils import parse_cli_stream_json_output


class GeminiCliLocalAnswerGenerator(GeminiCliAnswerGenerator):
    """An AnswerGenerator that uses the local gemini CLI."""

    async def run_cli_command(
        self,
        command_parts: list[str],
        extra_env: dict[str, str] = None,
    ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
        """Executes the gemini CLI command and returns the parsed JSON output and raw logs."""
        
        # Prepare environment
        import os
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)

        # Create subprocess
        proc = await asyncio.create_subprocess_exec(
            *command_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        stdout, stderr = await proc.communicate()

        stdout_str = stdout.decode()
        stderr_str = stderr.decode()

        # Initialize logs with stderr content first
        logs: list[TraceLogEvent] = []
        for line in stderr_str.splitlines():
            if line.strip():
                logs.append(
                    TraceLogEvent(
                        type="CLI_STDERR", source=self.name, content=line.strip()
                    )
                )

        # Always log full stdout for debugging/archival
        if stdout_str:
            logs.append(
                TraceLogEvent(
                    type="CLI_STDOUT_FULL", source=self.name, content=stdout_str
                )
            )

        # Parse stdout. If stream-json, parse events. Otherwise, treat as raw message.
        response_dict = {
            "stdout": stdout_str,
            "stderr": stderr_str,
            "exit_code": proc.returncode,
            "response": "",
        }
        if "--output-format" in command_parts and "stream-json" in command_parts:
            parsed_response_dict, parsed_logs = parse_cli_stream_json_output(stdout_str)
            response_dict.update(parsed_response_dict)
            logs.extend(parsed_logs)
        else:
            # If not stream-json, treat stdout as a single response message for logging purposes
            if stdout_str.strip():
                logs.append(
                    TraceLogEvent(
                        type="CLI_STDOUT_RAW",
                        source=self.name,
                        content=stdout_str.strip(),
                    )
                )
            response_dict["response"] = stdout_str.strip()  # Direct text response

        if proc.returncode != 0:
            error_msg = stderr_str.strip() or stdout_str.strip()
            raise RuntimeError(
                f"Gemini CLI failed with code {proc.returncode}: {error_msg}"
            )

        return response_dict, logs
