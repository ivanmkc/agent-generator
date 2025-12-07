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

# --- Concurrency Settings ---

# Global Concurrency: How many benchmark cases to run in parallel client-side.
# Increased to 400 to target <10m runtime by running all tests in parallel.
MAX_BENCHMARK_CONCURRENCY = 400

# Per-Instance Concurrency: How many requests a SINGLE Cloud Run container handles.
# Tested stable limit is 10 requests per 4GB/4CPU instance.
# Exceeding this causes OOM or CPU thrashing due to heavy Node.js CLI processes.
MAX_INSTANCE_CONCURRENCY = 10

# Max Instances: How many containers Cloud Run is allowed to spin up.
# 100 global requests / 10 per instance = 10 instances needed minimum.
# We set limit to 100 to allow practically unlimited scale-out.
MAX_CLOUD_RUN_INSTANCES = 100

# --- Resource Limits ---

# Optimized for stability/cost. 4Gi is sufficient for 10 concurrent requests.
CLOUD_RUN_MEMORY_LIMIT = "4Gi"
CLOUD_RUN_CPU_LIMIT = "4"