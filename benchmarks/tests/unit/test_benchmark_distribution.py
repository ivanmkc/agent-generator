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

""".
Regression test to ensure benchmark correct answers are reasonably distributed
and not biased towards a single option (e.g., 'A').

Dynamically discovers all MC benchmark files and verifies distribution both
per-file and globally.
"""

from collections import Counter
import math
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

import pytest
import yaml

# Define project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS_DIR = PROJECT_ROOT / "benchmarks" / "benchmark_definitions"


def get_mc_benchmark_files() -> List[Path]:
  """
  Discovers all benchmark.yaml files that contain multiple_choice questions.
  """
  mc_files = []
  if not DEFINITIONS_DIR.exists():
    return []

  for yaml_file in DEFINITIONS_DIR.rglob("benchmark.yaml"):
    try:
      with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)
        if not data or "benchmarks" not in data:
          continue

        # Check if at least one question is MC
        if any(
            bm.get("benchmark_type") == "multiple_choice"
            for bm in data["benchmarks"]
        ):
          mc_files.append(yaml_file)
    except Exception:
      continue

  return sorted(mc_files)


def calculate_bias_threshold(n_samples: int, n_options: int) -> float:
  """
  Calculates a dynamic threshold for the maximum allowable proportion of a single answer.

  Uses a statistical heuristic: Expected proportion (1/N) + Margin.
  Margin is derived from standard error (3 * sigma) to allow for random variance,
  plus a base buffer.

  For small N, the statistical bound is wide.
  """
  if n_samples == 0:
    return 1.0

  p = 1.0 / n_options if n_options > 0 else 1.0

  # Standard Error for proportion
  sigma = math.sqrt(p * (1 - p) / n_samples)

  # Allow 4 standard deviations (very loose) or a minimum practical buffer of 15%
  margin = 4 * sigma

  return p + margin


def check_distribution(answers: List[str], context_name: str):
  """
  Verifies that the answer distribution is not excessively skewed.
  """
  total = len(answers)
  if total < 10:
    # Too few samples to be statistically significant
    return

  counts = Counter(answers)
  unique_options = len(counts.keys())

  # Assume at least 4 options (A, B, C, D) typically, or use observed count if higher.
  # Most MC questions have 4-5 options.
  n_options_estimate = max(unique_options, 4)

  threshold = calculate_bias_threshold(total, n_options_estimate)

  most_common_opt, count = counts.most_common(1)[0]
  percentage = count / total

  print(f"\nDistribution for {context_name} (N={total}):")
  for k, v in sorted(counts.items()):
    print(f"  {k}: {v} ({v/total:.2%})")
  print(
      f"  -> Threshold: {threshold:.2%} (Expected ~{1/n_options_estimate:.2%})"
  )

  assert percentage < threshold, (
      f"Bias detected in {context_name}. Option '{most_common_opt}' appears"
      f" {count}/{total} times ({percentage:.2%}). Exceeds dynamic threshold of"
      f" {threshold:.2%}. "
  )


# --- Tests ---


@pytest.mark.parametrize("file_path", get_mc_benchmark_files())
def test_intra_file_distribution(file_path):
  """Checks distribution within each individual benchmark file."""
  with open(file_path, "r") as f:
    data = yaml.safe_load(f)

  answers = [
      bm.get("correct_answer")
      for bm in data["benchmarks"]
      if bm.get("benchmark_type") == "multiple_choice"
      and bm.get("correct_answer")
  ]

  check_distribution(
      answers, f"File: {file_path.name} ({file_path.parent.name})"
  )


def test_global_distribution():
  """Checks the aggregate distribution across all discovered MC files."""
  all_files = get_mc_benchmark_files()
  all_answers = []

  for file_path in all_files:
    with open(file_path, "r") as f:
      data = yaml.safe_load(f)

    all_answers.extend([
        bm.get("correct_answer")
        for bm in data["benchmarks"]
        if bm.get("benchmark_type") == "multiple_choice"
        and bm.get("correct_answer")
    ])

  check_distribution(all_answers, "GLOBAL (All MC Benchmarks)")
