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

"""An AnswerGenerator that uses the gemini CLI hosted in a local Podman container."""

import asyncio
import json
import os
import shutil
import re
import uuid
from pathlib import Path
from typing import Any, Optional
from colorama import init, Fore, Style
import aiohttp

# Initialize colorama
init()

from benchmarks.api_key_manager import API_KEY_MANAGER, ApiKeyManager, KeyType
from benchmarks.answer_generators.gemini_cli_answer_generator import GeminiCliAnswerGenerator
from benchmarks.data_models import TraceLogEvent
from benchmarks.utils import parse_cli_stream_json_output
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import ImageDefinition, IMAGE_DEFINITIONS, IMAGE_PREFIX
from benchmarks.answer_generators.hash_utils import calculate_source_hash
from benchmarks.answer_generators.gemini_cli_docker.podman_utils import PodmanContainer


class GeminiCliPodmanAnswerGenerator(GeminiCliAnswerGenerator):
    """
    An AnswerGenerator that uses the gemini CLI hosted in a local Podman container.
    Delegates container lifecycle to PodmanContainer.
    """

    def __init__(
        self,
        image_definitions: dict[str, ImageDefinition],
        image_name: str | None = None,
        dockerfile_dir: str | Path | None = None,
        model_name: str = "gemini-2.5-pro",
        context_instruction: str | None = None,
        service_url: str | None = None,
        api_key_manager: ApiKeyManager | None = None,
    ):
        self._image_definitions = image_definitions
        self.context_instruction = context_instruction
        
        # Resolve image name and dockerfile dir
        if image_name:
            self.image_name = image_name
            if dockerfile_dir:
                self.dockerfile_dir = Path(dockerfile_dir)
            elif image_name in image_definitions:
                def_ = image_definitions[image_name]
                self.dockerfile_dir = Path(__file__).parent / def_.source_dir
            else:
                 self.dockerfile_dir = None 
        elif dockerfile_dir:
            self.dockerfile_dir = Path(dockerfile_dir)
            self.image_name = f"gemini-cli:{self.dockerfile_dir.name}"
        else:
            raise ValueError("Either image_name or dockerfile_dir must be provided.")

        super().__init__(
            model_name=model_name,
            cli_path="gemini",
            context=self.context_instruction,
            api_key_manager=api_key_manager,
        )

        self._image_checked = False
        self._is_proxy = bool(service_url)
        self._base_url = service_url
        self._setup_completed = False
        self._setup_lock = asyncio.Lock()
        
        if not self._is_proxy:
            self.container = PodmanContainer(image_name=self.image_name)
        else:
            self.container = None

    @property
    def name(self) -> str:
        return (
            f"GeminiCliPodmanAnswerGenerator({self.model_name},"
            f" image={self.image_name})"
        )

    @property
    def description(self) -> str:
        image_def = self._image_definitions.get(self.image_name)
        content_desc = image_def.description if image_def else "Custom environment."
        
        desc = f"**Model:** {self.model_name}\n\n"
        desc += f"**Environment:** {content_desc}\n\n"
        
        if self._is_proxy:
            desc += f"*Note: Acting as a proxy to service at {self._base_url}.*"
        
        if self.context_instruction:
            desc += f"\n\n**Context Instruction:**\n> {self.context_instruction[:200]}..."
            
        return desc

    async def setup(self, force_deploy: bool = False) -> None:
        async with self._setup_lock:
            if self._setup_completed:
                return

            if self._is_proxy:
                self._setup_completed = True
                return

            print(f"[Podman Setup] Starting setup for {self.name}")
            await self._ensure_image_ready(force=force_deploy)

            # Start via PodmanContainer
            await self.container.start()
            self._base_url = self.container.base_url
            
            self._setup_completed = True
            print(f"[Podman Setup] Setup for {self.name} completed. Listening on {self._base_url}")

    async def teardown(self) -> None:
        if self.container:
            self.container.stop()

    async def _ensure_image_ready(self, force: bool = False):
        print(f"[Podman Ensure Image] Checking image readiness for {self.image_name}")
        if self._image_checked and not force:
            return

        if self.image_name in self._image_definitions:
            await self._build_image_chain(self.image_name, force=force)
            self._image_checked = True
            return

        raise RuntimeError(
            f"Image '{self.image_name}' is not a known managed image and no "
            "dockerfile_dir was provided for a custom build."
        )
    
    async def _get_image_label(self, image_name: str, label_key: str) -> str | None:
        try:
            inspect_cmd = ["podman", "inspect", "--format", f"{{{{.Config.Labels.{label_key}}}}}", image_name]
            proc = await asyncio.create_subprocess_exec(
                *inspect_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                val = stdout.decode().strip()
                return val if val != "<no value>" else None
        except Exception:
            pass
        return None

    async def _execute_podman_build(self, image_name: str, dockerfile_path: Path, context_path: Path, build_args: Optional[dict[str, str]] = None, labels: Optional[dict[str, str]] = None):
        print(f"Building Podman image: {image_name}...")
        build_cmd = ["podman", "build", "-t", image_name, "-f", str(dockerfile_path)]
        if build_args:
            for k, v in build_args.items():
                build_cmd.extend(["--build-arg", f"{k}={v}"])
        if labels:
            for k, v in labels.items():
                build_cmd.extend(["--label", f"{k}={v}"])
        build_cmd.append(str(context_path))

        proc = await asyncio.create_subprocess_exec(
            *build_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
             raise RuntimeError(f"Build failed for {image_name}: {stderr.decode()}")
        print(f"Successfully built {image_name}")

    async def _build_image_chain(self, image_key: str, force: bool = False) -> bool:
        definition = self._image_definitions[image_key]
        dependency_rebuilt = False
        for dep_key in definition.dependencies:
            if await self._build_image_chain(dep_key, force=force):
                dependency_rebuilt = True

        full_image_name = image_key
        base_path = Path(__file__).parent
        source_path = base_path / definition.source_dir
        dockerfile_path = base_path / definition.dockerfile

        current_hash = calculate_source_hash(source_path)
        should_build = force or dependency_rebuilt

        if not should_build:
            exists_cmd = ["podman", "image", "exists", full_image_name]
            proc = await asyncio.create_subprocess_exec(*exists_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
            await proc.communicate()
            if proc.returncode != 0:
                should_build = True
            else:
                existing_hash = await self._get_image_label(full_image_name, "source_hash")
                if existing_hash != current_hash:
                    should_build = True

        if should_build:
            await self._execute_podman_build(
                image_name=full_image_name,
                dockerfile_path=dockerfile_path,
                context_path=source_path,
                build_args=definition.build_args,
                labels={"source_hash": current_hash},
            )
            return True
        return False

    async def run_cli_command(
        self,
        command_parts: list[str],
        extra_env: dict[str, str] = None,
    ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
        if not self._setup_completed:
            await self.setup()

        full_args = list(command_parts)
        is_generation = "--model" in full_args
        if is_generation and self.context_instruction:
            full_args[-1] = self.context_instruction + full_args[-1]

        logs: list[TraceLogEvent] = []

        try:
            if self._is_proxy:
                 payload = {"args": full_args, "env": extra_env or {}}
                 async with aiohttp.ClientSession() as session:
                    async with session.post(self._base_url, json=payload) as resp:
                        if resp.status != 200:
                            raise RuntimeError(f"Proxy returned {resp.status}")
                        result = await resp.json()
            else:
                result = await self.container.send_command(full_args, extra_env)

        except Exception as e:
            raise RuntimeError(f"Failed to communicate with API server: {e}")

        stdout_str = result.get("stdout", "")
        stderr_str = result.get("stderr", "")
        returncode = result.get("returncode", 0)

        for line in stderr_str.splitlines():
            if line.strip():
                logs.append(TraceLogEvent(type="CLI_STDERR", source="podman_server", content=line.strip()))

        captured_error_report = None
        error_report_match = re.search(r"Error when talking to Gemini API Full report available at: (\S+)", stderr_str)
        if error_report_match:
            report_path = error_report_match.group(1)
            error_content = None
            if self.container:
                error_content = await self.container.read_file(report_path)
            
            if error_content:
                captured_error_report = error_content
                logs.append(TraceLogEvent(type="GEMINI_CLIENT_ERROR", source="podman_server", content=error_content))

        if stdout_str:
            logs.append(TraceLogEvent(type="CLI_STDOUT_FULL", source="podman_server", content=stdout_str))

        response_dict = {
            "stdout": stdout_str,
            "stderr": stderr_str,
            "exit_code": returncode,
            "response": "",
        }

        if "--output-format" in full_args and "stream-json" in full_args:
            parsed_response_dict, parsed_logs = parse_cli_stream_json_output(stdout_str)
            response_dict.update(parsed_response_dict)
            logs.extend(parsed_logs)
        else:
            if stdout_str.strip():
                logs.append(TraceLogEvent(type="CLI_STDOUT_RAW", source="podman_server", content=stdout_str.strip()))
            response_dict["response"] = stdout_str.strip()

        if returncode != 0:
            error_msg = stderr_str.strip() or stdout_str.strip()
            if captured_error_report:
                error_msg += f"\n\n[Captured Error Report]\n{captured_error_report}"
            raise RuntimeError(f"Gemini CLI failed with code {returncode}: {error_msg}")

        return response_dict, logs
