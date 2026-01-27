# Experiment Report: Statistical Discovery V45 (Task-Aware Solver)

**Date:** 2026-01-15
**Status:** **Success (Schema Fix Verified)**
**Agent Variant:** `ADK_TASK_AWARE_V45`
**Previous Best:** `ADK_KNOWLEDGE_V44`

## 1. Hypothesis & Configuration
**Hypothesis:** A unified "Task-Aware" solver that switches personas based on `benchmark_type` can handle the diverse requirements of API Understanding (Forensic Search), Fix Error (Coding), and Multiple Choice (Reasoning) better than a single generic solver.

**Configuration:**
*   **Unified Agent:** `TaskAwareSolverV45` (Loop).
*   **Mode Switching:** Dynamic system instruction based on `{benchmark_type}` placeholder.
*   **Modes:**
    *   `api_understanding`: Forensic API Researcher (Get Tree -> Search -> Verify Path).
    *   **Fix Error:** Senior Engineer (Analyze -> Search -> Fix Code).
    *   **Multiple Choice:** Exam Taker (Keywords -> Search -> Confirm).

## 2. Issue: Schema Mismatch
**Observation:** Early runs failed with `Input should be <BenchmarkType.API_UNDERSTANDING: 'api_understanding'> [type=literal_error, input_value='multiple_choice']`.
**Root Cause:** The `UniversalAnswer` schema lacked the `benchmark_type` field, or the agent defaulted to `multiple_choice` because it wasn't explicitly instructed to match the Pydantic discriminator field required by the polymorphic `AnswerOutput` model in `data_models.py`.

**Fix Implemented:**
1.  **Schema Update:** Added `benchmark_type: str` to `UniversalAnswer` in `experiment_65.py`.
2.  **Instruction Update:** Updated `AnswerFormatter` to explicitly set `benchmark_type` to the value of the `{benchmark_type}` context variable.

## 3. Experiment Progression (V35 -> V45)

The path from V35 to V45 represents a shift from **Output Mechanics** to **Cognitive Discipline**.

| Exp | Version | Focus | Key Innovation |
| :--- | :--- | :--- | :--- |
| **55** | V35 | Output Reliability | **External Formatter** (Decoupled formatting call to avoid JSON errors). |
| **56** | V36 | Code Accuracy | **Signature Verification Planner** (Sanitizer preserves signatures). |
| **57** | V37 | Architecture | **In-Chain Formatter** (Replaced external call with `RawClientFormatterAgent`). |
| **59** | V39 | Hallucination Fix | **Reactive Loop** (Agent must search/inspect/verify, no static retrieval). |
| **60** | V40 | Stability | **File-Based Handoff** (Writes `final_answer.json` to avoid teardown races). |
| **61** | V41 | API Accuracy | **Public API Bias** (Formatter prefers `google.adk` over internal paths). |
| **62** | V42 | Protocol | **Strict Reasoning Guidelines** ("Map First", "Evidence Required"). |
| **63** | V43 | Isolation | **Context Sandboxing** (Tools restricted to `repos/adk-python` source tree). |
| **64** | V44 | Verification | **Runtime Path Verification** (Agent must call `get_module_help` on final path). |
| **65** | V45 | Specialization | **Task-Aware Personas** (Dynamic mode switching based on benchmark type). |

## 4. Conclusion
V45 incorporates the "Reactive Loop" and "Strict Protocols" developed in V39-V44 but wraps them in a context-aware shell. This ensures that the agent uses the right *kind* of reasoning (Forensic vs. Constructive) for the task at hand. The schema fix ensures the output is compatible with the strict Pydantic validation of the benchmark harness.
