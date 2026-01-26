"""Podman Utils module."""

import asyncio
import atexit
import os
import socket
import subprocess
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
import aiohttp

from benchmarks.answer_generators.hash_utils import calculate_source_hash

class PodmanContainer:
    """
    Manages the lifecycle of a Gemini CLI Podman container.
    """

    def __init__(self, image_name: str, container_name: str = None, image_definitions: Optional[Dict[str, Any]] = None):
        self.image_name = image_name
        self.container_name = container_name or f"gemini-cli-podman-container-{uuid.uuid4().hex}"
        self.image_definitions = image_definitions
        self.base_url: Optional[str] = None
        self._port: Optional[int] = None
        self._setup_lock = asyncio.Lock()
        self._is_running = False
        self._image_checked = False

    async def start(self, force_build: bool = False):
        """Starts the container if not already running."""
        async with self._setup_lock:
            if self._is_running:
                return

            if self.image_definitions:
                await self._ensure_image_ready(force=force_build)

            # Find a free port
            with socket.socket() as s:
                s.bind(("", 0))
                self._port = s.getsockname()[1]

            self.base_url = f"http://localhost:{self._port}"

            print(
                f"Starting Podman container {self.container_name} on port {self._port}..."
            )

            # Build command
            cmd = [
                "podman",
                "run",
                "-d",
                "--rm",
                "--name",
                self.container_name,
                "-p",
                f"{self._port}:8080",
            ]

            # Pass through common credentials/env vars
            env_vars = [
                "GEMINI_API_KEY",
                "GOOGLE_GENAI_USE_VERTEXAI",
                "GOOGLE_CLOUD_PROJECT",
                "GOOGLE_CLOUD_LOCATION",
                "CONTEXT7_API_KEY",
                "GOOGLE_API_KEY",
            ]
            for var in env_vars:
                if os.environ.get(var):
                    cmd.extend(["-e", var])

            # Handle ADC credentials mount
            adc_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if adc_path:
                container_path = "/tmp/google_credentials.json"
                cmd.extend(["-v", f"{adc_path}:{container_path}"])
                cmd.extend(["-e", f"GOOGLE_APPLICATION_CREDENTIALS={container_path}"])

            cmd.append(self.image_name)

            # Start container
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(
                    f"Failed to start podman container: {stderr.decode()}"
                )

            # Register cleanup
            atexit.register(self.stop)

            # Wait for health check
            await self._wait_for_health()
            self._is_running = True

    async def _ensure_image_ready(self, force: bool = False):
        if self._image_checked and not force:
            return

        if self.image_name in self.image_definitions:
            await self._build_image_chain(self.image_name, force=force)
            self._image_checked = True
            return

        # If it's not a managed image, we assume it's a pre-built image (like localhost/...)
        # We check if it exists, but don't try to build it.
        exists_cmd = ["podman", "image", "exists", self.image_name]
        proc = await asyncio.create_subprocess_exec(*exists_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        if proc.returncode != 0:
             raise RuntimeError(f"Image '{self.image_name}' is not found in Podman and is not a known managed image.")
        self._image_checked = True

    async def _build_image_chain(self, image_key: str, force: bool = False) -> bool:
        definition = self.image_definitions[image_key]
        dependency_rebuilt = False
        for dep_key in definition.dependencies:
            if await self._build_image_chain(dep_key, force=force):
                dependency_rebuilt = True

        full_image_name = image_key
        # We assume the utility is in the same directory structure relative to the generators
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

    async def _execute_podman_build(self, image_name: str, dockerfile_path: Path, context_path: Path, build_args: Optional[Dict[str, str]] = None, labels: Optional[Dict[str, str]] = None):
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

    async def _wait_for_health(self):
        """Waits for the container server to be ready."""
        print(f"Waiting for {self.container_name} to be ready...")
        for _ in range(20):
            try:
                async with aiohttp.ClientSession() as session:
                    # Simple health check on root
                    async with session.get(self.base_url, timeout=2.0) as resp:
                        if resp.status == 200:
                            return
            except Exception:
                pass
            await asyncio.sleep(0.5)

        # If timeout, try to get logs
        self.stop()
        raise RuntimeError(f"Container {self.container_name} failed to start.")

    def stop(self):
        """Stops the container."""
        if not self._is_running:
            return

        # Unregister atexit
        atexit.unregister(self.stop)

        try:
            subprocess.run(
                ["podman", "kill", self.container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass
        finally:
            self._is_running = False

    async def send_command(
        self, args: List[str], env: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Sends a command to the container.
        """
        if not self._is_running:
            await self.start()

        payload = {"args": args, "env": env or {}}

        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, json=payload, timeout=120.0) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Podman server returned {resp.status}: {text}")

                return await resp.json()

    async def read_file(self, path: str) -> Optional[str]:
        """Reads a file from the container."""
        if not self._is_running:
            return None

        read_payload = {"path": path}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/read_file", json=read_payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("content", "")
                else:
                    return None