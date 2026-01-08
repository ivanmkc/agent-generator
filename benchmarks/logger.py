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
import contextlib
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Any
from typing import Optional
from typing import List
from typing import TYPE_CHECKING

from colorama import Fore, Style, init

if TYPE_CHECKING:
    from benchmarks.data_models import BenchmarkRunResult

# Initialize colorama
init(autoreset=True)


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
        suite: str,
        validation_error: Optional[str],
        temp_test_file: Optional[Path],
        answer_data: Optional[dict] = None,
        trace_logs: Optional[list[Any]] = None,
        generation_attempts: Optional[list[Any]] = None,
    ) -> None:
        """Logs the result of a test execution."""
        pass
    
    @abc.abstractmethod
    def log_summary_table(self, results: List[BenchmarkRunResult]) -> None:
        """Logs a summary table of all benchmark results."""
        pass

    @abc.abstractmethod
    def finalize_run(self) -> None:
        """Called at the end of a benchmark run to perform any final logging/cleanup."""
        pass

    @contextlib.contextmanager
    def section(self, name: str) -> None:
        """Context manager for a hierarchical section."""
        yield


class ConsoleBenchmarkLogger(BenchmarkLogger):
    """A benchmark logger that prints messages to the console."""

    def __init__(self):
        self._indent_level = 0

    def _print(self, msg: str, color: str = ""):
        indent = "  " * self._indent_level
        print(f"{indent}{color}{msg}{Style.RESET_ALL}")

    @contextlib.contextmanager
    def section(self, name: str):
        self._print(f"▶ {name}", Fore.CYAN + Style.BRIGHT)
        self._indent_level += 1
        try:
            yield
        finally:
            self._indent_level -= 1

    def log_message(self, message: str) -> None:
        self._print(message)

    def log_generation_failure(
        self, benchmark_name: str, error_message: str, prompt: str
    ) -> None:
        self._print(f"❌ GENERATION FAILED for {benchmark_name}", Fore.RED)
        self._print(f"Error: {error_message}", Fore.RED)
        # self._print(f"Prompt:\n{prompt}\n") # Optional: too verbose for console?

    def log_test_result(
        self,
        benchmark_name: str,
        result: str,
        suite: str,
        validation_error: Optional[str],
        temp_test_file: Optional[Path],
        answer_data: Optional[dict] = None,
        trace_logs: Optional[list[Any]] = None,
        generation_attempts: Optional[list[Any]] = None,
    ) -> None:
        is_pass = result == "pass"
        status_color = Fore.GREEN if is_pass else Fore.RED
        status_icon = "✔" if is_pass else "✘"
        
        # We assume this is called inside a 'Benchmark Suite' section or similar context
        # But since cases run in parallel, we want a self-contained block for the case.
        
        # Indent specifically for this case block
        with self.section(f"Case: {benchmark_name} (Suite: {suite})"):
            # Log attempts if provided
            if generation_attempts:
                for attempt in generation_attempts:
                    # attempt is a GenerationAttempt object or dict. Assuming object based on orchestrator.
                    # We need to handle if it's a dict or object. 
                    # Based on codebase, it's a Pydantic model usually, but let's be safe.
                    
                    attr_getter = lambda x, k: getattr(x, k) if hasattr(x, k) else x.get(k)
                    
                    a_num = attr_getter(attempt, "attempt_number")
                    a_status = attr_getter(attempt, "status")
                    a_error = attr_getter(attempt, "error_message")
                    a_key = attr_getter(attempt, "api_key_id")
                    
                    key_str = f" (Key: {a_key})" if a_key else ""
                    
                    if a_status == "success":
                         self._print(f"Attempt {a_num}: Success{key_str}", Fore.GREEN)
                    else:
                         self._print(f"Attempt {a_num}: Failed - {a_error}{key_str}", Fore.YELLOW)

            if validation_error:
                self._print(f"Validation Error: {validation_error}", Fore.RED)
            
            self._print(f"Result: {result.upper()} {status_icon}", status_color)
            if not is_pass and temp_test_file:
                 self._print(f"Reproduce: {temp_test_file}", Fore.LIGHTBLACK_EX)

    def log_summary_table(self, results: List[BenchmarkRunResult]) -> None:
        """Prints a summary table to the console."""
        if not results:
            self._print("No results to display.", Fore.YELLOW)
            return

        # Calculate widths
        max_name_len = max(len(r.benchmark_name) for r in results)
        max_name_len = max(max_name_len, len("Benchmark"))
        max_name_len = min(max_name_len, 50) # Cap width

        # Headers
        headers = f"{'Benchmark':<{max_name_len}} | {'Result':<10} | {'Duration':<8} | {'Attempts'}"
        separator = "-" * len(headers)
        
        print("\n")
        self._print("SUMMARY TABLE", Fore.CYAN + Style.BRIGHT)
        self._print(separator)
        self._print(headers)
        self._print(separator)

        for res in results:
            name = res.benchmark_name
            if len(name) > max_name_len:
                name = name[:max_name_len-3] + "..."
            
            is_pass = res.status == "pass"
            color = Fore.GREEN if is_pass else Fore.RED
            status_str = "PASS" if is_pass else "FAIL"
            
            attempts_count = len(res.generation_attempts) if res.generation_attempts else 0
            
            row = f"{name:<{max_name_len}} | {status_str:<10} | {res.latency:6.2f}s | {attempts_count}"
            self._print(row, color)
        
        self._print(separator)
        
        # Stats
        total = len(results)
        passed = sum(1 for r in results if r.status == "pass")
        failed = total - passed
        pass_rate = (passed / total) * 100 if total > 0 else 0
        
        self._print(f"Total: {total}, Passed: {passed}, Failed: {failed} ({pass_rate:.1f}%)", Fore.CYAN)
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

    @contextlib.contextmanager
    def section(self, name: str):
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(f"\n## Section: {name}\n\n")
        yield

    def log_message(self, message: str) -> None:
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(f"- {message}\n")

    def log_generation_failure(
        self, benchmark_name: str, error_message: str, prompt: str
    ) -> None:
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(f"### ❌ Generation Failed: {benchmark_name}\n")
            f.write(f"**Error:** {error_message}\n")
            f.write(f"### Prompt\n```\n{prompt}\n```\n\n")

    def log_test_result(
        self,
        benchmark_name: str,
        result: str,
        suite: str,
        validation_error: Optional[str],
        temp_test_file: Optional[Path],
        answer_data: Optional[dict] = None,
        trace_logs: Optional[list[Any]] = None,
        generation_attempts: Optional[list[Any]] = None,
    ) -> None:
        status_icon = "✅" if result == "pass" else "❌"
        status_text = "PASSED" if result == "pass" else "FAILED"
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(f"### {status_icon} Test {status_text}: {benchmark_name} (Suite: {suite})\n")
            if generation_attempts:
                f.write("**Generation Attempts:**\n")
                for att in generation_attempts:
                     # Handle Pydantic or dict
                     att_data = att.model_dump() if hasattr(att, "model_dump") else att
                     f.write(f"- {att_data}\n")
            
            if validation_error:
                f.write(f"**Validation Error:** {validation_error}\n")
            if temp_test_file:
                f.write(f"**Temp Test File:** `{temp_test_file}`\n")
            if answer_data:
                f.write("**Generated Answer:**\n")
                f.write(f"```json\n{json.dumps(answer_data, indent=2, cls=BytesEncoder)}\n```\n")
            if trace_logs:
                f.write("**Trace Logs:**\n")
                try:
                    logs_data = [
                        t.model_dump(mode='json') if hasattr(t, "model_dump") else t
                        for t in trace_logs
                    ]
                    f.write(f"```json\n{json.dumps(logs_data, indent=2, cls=BytesEncoder)}\n```\n")
                except Exception:
                    f.write(f"```\n{str(trace_logs)}\n```\n")
            f.write("\n")

    def log_summary_table(self, results: List[BenchmarkRunResult]) -> None:
        """Logs a summary table to the markdown file."""
        if not results:
            return

        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write("\n## Summary Table\n\n")
            f.write("| Benchmark | Result | Duration | Attempts |\n")
            f.write("| :--- | :---: | :---: | :---: |\n")
            
            for res in results:
                status_icon = "✅ PASS" if res.status == "pass" else "❌ FAIL"
                attempts_count = len(res.generation_attempts) if res.generation_attempts else 0
                f.write(f"| {res.benchmark_name} | {status_icon} | {res.latency:.2f}s | {attempts_count} |\n")
            
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


class BytesEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle bytes and set objects."""
    def default(self, obj):
        if isinstance(obj, bytes):
            return repr(obj)
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)

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
            f.write(json.dumps(entry, cls=BytesEncoder) + "\n")
    
    @contextlib.contextmanager
    def section(self, name: str):
        self._log_event("section_start", {"name": name})
        yield
        self._log_event("section_end", {"name": name})

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
        suite: str,
        validation_error: Optional[str],
        temp_test_file: Optional[Path],
        answer_data: Optional[dict] = None,
        trace_logs: Optional[list[Any]] = None,
        generation_attempts: Optional[list[Any]] = None,
    ) -> None:
        # Convert trace_logs to dicts if they are Pydantic models
        logs_data = None
        if trace_logs:
            logs_data = [
                t.model_dump(mode='json') if hasattr(t, "model_dump") else t for t in trace_logs
            ]
        
        attempts_data = None
        if generation_attempts:
            attempts_data = [
                a.model_dump(mode='json') if hasattr(a, "model_dump") else a for a in generation_attempts
            ]

        self._log_event(
            "test_result",
            {
                "benchmark_name": benchmark_name,
                "result": result,
                "suite": suite,
                "validation_error": validation_error,
                "temp_test_file": str(temp_test_file) if temp_test_file else None,
                "answer_data": answer_data,
                "trace_logs": logs_data,
                "generation_attempts": attempts_data,
            },
        )
    
    def log_summary_table(self, results: List[BenchmarkRunResult]) -> None:
        """Logs the summary table as a structured event."""
        summary_data = []
        for res in results:
            summary_data.append({
                "benchmark_name": res.benchmark_name,
                "status": res.status,
                "latency": res.latency,
                "attempts_count": len(res.generation_attempts) if res.generation_attempts else 0
            })
        
        self._log_event("summary_table", {"results": summary_data})

    def finalize_run(self) -> None:
        end_time = time.time()
        duration = end_time - self.start_time
        self._log_event("run_end", {"duration": duration})
        print(f"JSON trace log written to {self.output_file}")


class CompositeLogger(BenchmarkLogger):
    """A benchmark logger that forwards calls to multiple other loggers."""

    def __init__(self, loggers: List[BenchmarkLogger]):
        self.loggers = loggers

    def log_message(self, message: str) -> None:
        for logger in self.loggers:
            logger.log_message(message)

    def log_generation_failure(
        self, benchmark_name: str, error_message: str, prompt: str
    ) -> None:
        for logger in self.loggers:
            logger.log_generation_failure(benchmark_name, error_message, prompt)

    def log_test_result(
        self,
        benchmark_name: str,
        result: str,
        suite: str,
        validation_error: Optional[str],
        temp_test_file: Optional[Path],
        answer_data: Optional[dict] = None,
        trace_logs: Optional[list[Any]] = None,
        generation_attempts: Optional[list[Any]] = None,
    ) -> None:
        for logger in self.loggers:
            logger.log_test_result(
                benchmark_name,
                result,
                suite,
                validation_error,
                temp_test_file,
                answer_data,
                trace_logs,
                generation_attempts,
            )

    def log_summary_table(self, results: List[BenchmarkRunResult]) -> None:
        for logger in self.loggers:
            logger.log_summary_table(results)

    def finalize_run(self) -> None:
        for logger in self.loggers:
            logger.finalize_run()

    @contextlib.contextmanager
    def section(self, name: str):
        with contextlib.ExitStack() as stack:
            for logger in self.loggers:
                stack.enter_context(logger.section(name))
            yield
