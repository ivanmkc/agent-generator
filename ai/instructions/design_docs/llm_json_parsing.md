# Design Doc: Robust LLM-Based JSON Extraction

**Status:** Implemented
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Benchmark validation relies on the agent outputting valid JSON conforming to a specific schema. Agents often output:
- Markdown blocks.
- Conversational preambles.
- Malformed JSON.

Simple regex extraction is brittle.

## 2. Solution: Validation-Phase Sanitization
We introduce a **Parsing Layer** in the `BenchmarkRunner` (validation phase), not the Generator. This ensures the raw output of the agent is preserved, but the evaluation is robust to formatting errors.

### Workflow
1.  **Generator:** Produces `GeneratedAnswer`. If parsing fails, `output` is `None` and `raw_output` contains the text.
2.  **BenchmarkRunner:** Calls `ensure_valid_output`.
    - Checks if `output` is already valid.
    - If not, invokes `JsonSanitizer` on `raw_output`.
3.  **JsonSanitizer:**
    - **Stage 1:** Direct JSON Parse.
    - **Stage 2:** Regex Extraction (Code Blocks).
    - **Stage 3:** LLM Extraction (Smart Repair).
        - **Model:** Uses `MOST_POWERFUL_MODEL` (e.g., `gemini-3-pro-preview`) to ensure high-quality extraction and syntax repair.
        - **Prompt:** "Extract valid JSON matching schema... Fix syntax errors."

## 3. Architecture
- **Component:** `benchmarks/parsing/json_sanitizer.py`.
- **Integration:** `BenchmarkRunner.ensure_valid_output` in `benchmarks/benchmark_runner.py`.
- **Config:** `MOST_POWERFUL_MODEL` constant in `benchmarks/config.py`.

## 4. Benefits
- **Robustness:** Handles conversational output and minor syntax errors.
- ** Separation of Concerns:** Generator focuses on content; Runner handles formatting validation.
- **Consistency:** All benchmarks use the same high-quality extraction logic.