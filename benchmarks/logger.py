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

"""Logging utilities for benchmarks."""

from __future__ import annotations

import abc
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Any
from typing import Optional


class BenchmarkLogger(abc.ABC):
  """Abstract base class for benchmark loggers."""

  @abc.abstractmethod
  def log_message(self, message: str) -> None:
    """Logs a general message."""
    pass

  @abc.abstractmethod
  def log_generation_failure(
      self, benchmark_name: str, error_message: str, prompt: str
  ) -> None:
    """Logs a failure during answer generation."""
    pass

  @abc.abstractmethod
  def log_test_result(
      self,
      benchmark_name: str,
      result: str,
      validation_error: Optional[str],
      temp_test_file: Optional[Path],
      answer_data: Optional[dict] = None,
  ) -> None:
    """Logs the result of a test execution."""
    pass

  @abc.abstractmethod
  def finalize_run(self) -> None:
    """Called at the end of a benchmark run to perform any final logging/cleanup."""
    pass


class ConsoleBenchmarkLogger(BenchmarkLogger):
  """A benchmark logger that prints messages to the console."""

  def log_message(self, message: str) -> None:
    print(message)

  def log_generation_failure(
      self, benchmark_name: str, error_message: str, prompt: str
  ) -> None:
    print(f"--- GENERATION FAILED for {benchmark_name} ---")
    print(f"Error: {error_message}")
    print(f"Prompt:\n{prompt}\n")

  def log_test_result(
      self,
      benchmark_name: str,
      result: str,
      validation_error: Optional[str],
      temp_test_file: Optional[Path],
      answer_data: Optional[dict] = None,
  ) -> None:
    status = "PASSED" if result == "pass" else "FAILED"
    print(f"--- TEST {status} for {benchmark_name} ---")
    if validation_error:
      print(f"Validation Error: {validation_error}")
    if temp_test_file:
      print(f"Temp Test File: {temp_test_file}")
    print("\n")

  def finalize_run(self) -> None:
    print("Benchmark run finalized (console output).")


class TraceMarkdownLogger(BenchmarkLogger):
  """A benchmark logger that writes detailed trace information to a Markdown file."""

  def __init__(self, output_file: Path | str = "trace.md"):
    self.output_file = Path(output_file)
    self.start_time = time.time()
    self.output_file.write_text(
        f"# Benchmark Trace Log - {time.ctime(self.start_time)}\n\n",
        encoding="utf-8",
    )

  def log_message(self, message: str) -> None:
    with open(self.output_file, "a", encoding="utf-8") as f:
      f.write(f"- {message}\n")

  def log_generation_failure(
      self, benchmark_name: str, error_message: str, prompt: str
  ) -> None:
    with open(self.output_file, "a", encoding="utf-8") as f:
      f.write(f"## ❌ Generation Failed: {benchmark_name}\n")
      f.write(f"**Error:** {error_message}\n")
      f.write(f"### Prompt\n```\n{prompt}\n```\n\n")

  def log_test_result(
      self,
      benchmark_name: str,
      result: str,
      validation_error: Optional[str],
      temp_test_file: Optional[Path],
      answer_data: Optional[dict] = None,
  ) -> None:
    status_icon = "✅" if result == "pass" else "❌"
    status_text = "PASSED" if result == "pass" else "FAILED"
    with open(self.output_file, "a", encoding="utf-8") as f:
      f.write(f"## {status_icon} Test {status_text}: {benchmark_name}\n")
      if validation_error:
        f.write(f"**Validation Error:** {validation_error}\n")
      if temp_test_file:
        f.write(f"**Temp Test File:** `{temp_test_file}`\n")
      if answer_data:
        f.write("**Generated Answer:**\n")
        f.write(f"```json\n{json.dumps(answer_data, indent=2)}\n```\n")
      f.write("\n")

  def finalize_run(self) -> None:
    end_time = time.time()
    duration = end_time - self.start_time
    with open(self.output_file, "a", encoding="utf-8") as f:
      f.write(
          "\n---\n**Benchmark run finalized.** Total duration:"
          f" {duration:.2f} seconds.\n"
      )
    print(f"Trace log written to {self.output_file}")


class JsonTraceLogger(BenchmarkLogger):
  """A benchmark logger that writes structured JSONL trace information to a unique file per run."""

  def __init__(
      self,
      output_dir: Path | str = "benchmarks/traces",
      filename: Optional[str] = None,
  ):
    self.output_dir = Path(output_dir)
    self.output_dir.mkdir(parents=True, exist_ok=True)
    if filename:
      self.output_file = self.output_dir / filename
    else:
      timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
      self.output_file = self.output_dir / f"trace_{timestamp}.jsonl"
    self.start_time = time.time()
    self._log_event("run_start", {"timestamp": self.start_time})
    print(f"JSON trace log will be written to {self.output_file}")

  def _log_event(self, event_type: str, data: dict[str, Any]) -> None:
    entry = {"event_type": event_type, "timestamp": time.time(), "data": data}
    with open(self.output_file, "a", encoding="utf-8") as f:
      f.write(json.dumps(entry) + "\n")

  def log_message(self, message: str) -> None:
    self._log_event("message", {"message": message})

  def log_generation_failure(
      self, benchmark_name: str, error_message: str, prompt: str
  ) -> None:
    self._log_event(
        "generation_failure",
        {
            "benchmark_name": benchmark_name,
            "error_message": error_message,
            "prompt": prompt,
        },
    )

  def log_test_result(
      self,
      benchmark_name: str,
      result: str,
      validation_error: Optional[str],
      temp_test_file: Optional[Path],
      answer_data: Optional[dict] = None,
  ) -> None:
    self._log_event(
        "test_result",
        {
            "benchmark_name": benchmark_name,
            "result": result,
            "validation_error": validation_error,
            "temp_test_file": str(temp_test_file) if temp_test_file else None,
            "answer_data": answer_data,
        },
    )

  def finalize_run(self) -> None:
    end_time = time.time()
    duration = end_time - self.start_time
    self._log_event("run_end", {"duration": duration})
    print(f"JSON trace log written to {self.output_file}")
