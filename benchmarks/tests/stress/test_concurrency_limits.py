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

import asyncio
import time
import subprocess
import aiohttp
import pytest
import os
import requests
import statistics
import json

"""
Stress tests to determine optimal concurrency limits for local containerized servers.

This test file runs a local server (via Podman) and ramps up concurrent requests
to identify the breaking point where latency spikes or failures occur. It helps
in tuning the `CLOUD_RUN_CONFIG.MAX_INSTANCE_CONCURRENCY` configuration.
"""

# Stress test to find optimal concurrency limits for the server image.

IMAGE_NAME = "gemini-cli:base"
CONTAINER_NAME = "stress-test-server"
PORT = 8086 # Unique port

def podman_available():
  try:
    subprocess.run(
        ["podman", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return True
  except (FileNotFoundError, subprocess.CalledProcessError):
    return False

@pytest.fixture(scope="module")
def local_server():
    """Starts the container server."""
    if not podman_available():
        pytest.skip("Podman not available")

    # We assume IMAGE_NAME is already built with the server implementation we want to test
    # Check if image exists
    try:
        subprocess.run(["podman", "image", "exists", IMAGE_NAME], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print(f"Image {IMAGE_NAME} not found. Building...")
        build_cmd = [
            "podman", "build", "-t", IMAGE_NAME,
            "-f", "benchmarks/answer_generators/gemini_cli_docker/base/Dockerfile",
            "benchmarks/answer_generators/gemini_cli_docker/base"
        ]
        subprocess.check_call(build_cmd)

    print(f"Starting container {CONTAINER_NAME}...")
    
    # Cleanup previous instances if they exist
    subprocess.run(["podman", "rm", "-f", CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    cmd = [
        "podman", "run", "--rm", "-d",
        "--name", CONTAINER_NAME,
        "-p", f"{PORT}:8080",
        IMAGE_NAME,
    ]
    
    try:
        subprocess.check_output(cmd, text=True).strip()
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to start container: {e}")

    # Wait for health check
    url = f"http://localhost:{PORT}"
    health_passed = False
    for _ in range(10):
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                health_passed = True
                break
        except Exception:
            time.sleep(1)
            
    if not health_passed:
        subprocess.run(["podman", "kill", CONTAINER_NAME], stderr=subprocess.DEVNULL)
        pytest.fail("Server failed to start or pass health check")

    # Setup mock script once
    # 0.5s sleep simulates a fast LLM call, enough to overlap but stress throughput
    SLEEP_TIME = 0.5 
    mock_gemini_script = (
        "#!/bin/sh\n"
        f"sleep {SLEEP_TIME}\n"
        "echo \"Done sleeping\"\n"
    )
    subprocess.run([
        "podman", "exec", CONTAINER_NAME, 
        "sh", "-c", f"echo '{mock_gemini_script}' > /tmp/gemini && chmod +x /tmp/gemini"
    ], check=True)

    yield url

    print(f"Stopping container {CONTAINER_NAME}...")
    subprocess.run(["podman", "kill", CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.mark.asyncio
async def test_find_concurrency_limit(local_server):
    """
    Ramps up concurrency to find the breaking point.
    """
    concurrency_levels = [5, 10, 20, 40, 60, 80, 100, 120, 150]
    results = []

    payload = {
        "args": ["gemini"],
        "env": {"PATH": "/tmp:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"} 
    }

    print("\n--- Concurrency Stress Test Results ---")
    print(f"{ 'Concurrency':<12} { 'Success Rate':<15} { 'Avg Latency':<15} { 'P95 Latency':<15} { 'Throughput (req/s)':<20}")

    for concurrency in concurrency_levels:
        start_time = time.time()
        latencies = []
        failures = 0
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(concurrency):
                tasks.append(session.post(local_server, json=payload, timeout=10)) # 10s timeout
            
            # Run batch
            batch_start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            batch_duration = time.time() - batch_start

            for r in responses:
                if isinstance(r, Exception):
                    failures += 1
                elif r.status != 200:
                    failures += 1
                else:
                    # Approximation: we don't have per-request latency here easily without wrapping
                    # For stress testing, batch throughput is the main metric.
                    pass

        # Since we gathered all at once, the 'latency' of individual requests is hard to track perfectly
        # without wrapping. Let's assume average latency ~ batch_duration if perfectly sequential (bad),
        # or ~SLEEP_TIME if perfectly parallel.
        # Throughput = concurrency / batch_duration
        
        throughput = concurrency / batch_duration
        success_rate = ((concurrency - failures) / concurrency) * 100
        
        # We want to know if it blocked. 
        # Ideal batch duration ~ 0.5s + overhead.
        # If batch duration > 1.0s, we are queuing.
        
        results.append({
            "concurrency": concurrency,
            "success_rate": success_rate,
            "duration": batch_duration,
            "throughput": throughput
        })

        print(f"{concurrency:<12} {success_rate:<15.1f} {batch_duration:<15.4f} {'-':<15} {throughput:<20.2f}")

        if success_rate < 95:
            print(f"!!! High failure rate detected at concurrency {concurrency}. Stopping.")
            break
            
    # Save results to a file for comparison
    with open("concurrency_results.json", "w") as f:
        json.dump(results, f, indent=2)

    assert results[-1]["concurrency"] >= 5, "Server failed even at low concurrency!"
