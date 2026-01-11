import asyncio
import atexit
import os
import socket
import subprocess
import uuid
from typing import Optional, Dict, Any, List
import aiohttp

class PodmanContainer:
    """
    Manages the lifecycle of a Gemini CLI Podman container.
    """

    def __init__(self, image_name: str, container_name: str = None):
        self.image_name = image_name
        self.container_name = container_name or f"vibeshare-{uuid.uuid4().hex[:8]}"
        self.base_url: Optional[str] = None
        self._port: Optional[int] = None
        self._setup_lock = asyncio.Lock()
        self._is_running = False

    async def start(self):
        """Starts the container if not already running."""
        async with self._setup_lock:
            if self._is_running:
                return

            # Find a free port
            with socket.socket() as s:
                s.bind(('', 0))
                self._port = s.getsockname()[1]
            
            self.base_url = f"http://localhost:{self._port}"

            print(f"Starting Podman container {self.container_name} on port {self._port}...")
            
            # Build command
            cmd = [
                "podman", "run", "-d", "--rm",
                "--name", self.container_name,
                "-p", f"{self._port}:8080"
            ]

            # Pass through common credentials/env vars
            env_vars = [
                "GEMINI_API_KEY",
                "GOOGLE_GENAI_USE_VERTEXAI",
                "GOOGLE_CLOUD_PROJECT",
                "GOOGLE_CLOUD_LOCATION",
                "CONTEXT7_API_KEY",
                "GOOGLE_API_KEY"
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
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Failed to start podman container: {stderr.decode()}")

            # Register cleanup
            atexit.register(self.stop)

            # Wait for health check
            await self._wait_for_health()
            self._is_running = True

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
                check=False
            )
        except Exception:
            pass
        finally:
            self._is_running = False

    async def send_command(self, args: List[str], env: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Sends a command to the container.
        """
        if not self._is_running:
            await self.start()

        payload = {
            "args": args,
            "env": env or {}
        }

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
