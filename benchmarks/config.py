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

"""Configuration constants for benchmarks."""

from dataclasses import dataclass

@dataclass(frozen=True)
class CloudRunConfig:
    """Configuration settings for Cloud Run environment."""
    # Global Concurrency: How many benchmark cases to run in parallel client-side.
    # Cloud Run scales horizontally, so this can be high.
    MAX_GLOBAL_CONCURRENCY: int = 400
    
    # Per-Instance Concurrency: How many requests a SINGLE Cloud Run container handles.
    # Tested stable limit is 10 requests per 4GB/4CPU instance.
    MAX_INSTANCE_CONCURRENCY: int = 10
    
    # Max Instances: How many containers Cloud Run is allowed to spin up.
    MAX_INSTANCES: int = 100
    
    # Resource Limits
    MEMORY_LIMIT: str = "4Gi"
    CPU_LIMIT: str = "4"

@dataclass(frozen=True)
class PodmanConfig:
    """Configuration settings for local Podman environment."""
    # Global Concurrency: Constrained by local machine resources (CPU/RAM).
    # 10 was tested for a machine with the following specs: Apple M4 Pro, 48GB RAM
    # The podman machine was provisioned with the following resources: 7 CPUs, 8GB RAM
    MAX_GLOBAL_CONCURRENCY: int = 10

# Instantiate for usage
CLOUD_RUN_CONFIG = CloudRunConfig()
PODMAN_CONFIG = PodmanConfig()
