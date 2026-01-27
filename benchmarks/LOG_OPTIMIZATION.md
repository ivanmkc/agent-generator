# Benchmark Log Optimization Rationale

This document explains the strategy for managing the size of benchmark log artifacts (`results.json` and `trace.yaml`).

## The Problem: Log Bloat
During large-scale benchmark runs, log files were reaching several gigabytes in size. Analysis revealed that over 95% of this space was consumed by redundant copies of the same data, particularly large tool outputs (1MB+).

### Sources of Redundancy
1.  **Event Duality**: `TOOL_RESULT` events stored the output string in both the `tool_output` field and the raw `details` field (2x bloat).
2.  **Stream Duplication**: When using `--output-format stream-json`, the system logged both the `CLI_STDOUT_FULL` (the raw line) and the individual parsed events (another 2x bloat).
3.  **Error Context**: `GEMINI_CLIENT_ERROR` events logged the entire conversation history (including previous huge tool outputs) as "context", which is already stored in the preceding trace events.
4.  **History Multiplication**: `trace_logs` are stored in both the top-level result and the `generation_attempts` history, multiplying all the above bloats by the number of retries.

## The Solution: Intelligent Deduplication
The optimization strategy focuses on removing **structurally redundant** data without losing **unique information**.

### 1. Tool Result Deduplication
In `benchmarks/utils.py`, the `deduplicate_trace_logs` function removes the `details` field from `TOOL_RESULT` events. 
*   **Rationale**: The relevant data has already been parsed into `tool_output`.

### 2. Stream-JSON Optimization
In the `GeminiCli` AnswerGenerators, `CLI_STDOUT_FULL` is only logged if the output is *not* being parsed as `stream-json`.
*   **Rationale**: If parsing is successful, `parsed_logs` captures all information as individual events. Any unparseable lines are captured as `CLI_STDOUT_RAW`.

### 3. Error Context Compaction
The `deduplicate_trace_logs` function parses `GEMINI_CLIENT_ERROR` payloads and truncates `functionResponse` fields within the `context` list.
*   **Rationale**: The history leading up to an error is already present in the trace logs. We keep the error message and the structure of the history but remove the massive redundant payloads.

## Impact
These changes reduce the size of individual large events (like those found in `api_understanding` or `fix_errors`) from ~2.4MB to ~50KB, allowing for much more efficient storage and faster loading in the benchmark viewer.
