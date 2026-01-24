# Design Doc: Robust LLM-Based JSON Extraction

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Benchmark validation relies on the agent outputting valid JSON conforming to a specific schema (e.g., `FixErrorAnswerOutput`). Agents often output:
- Markdown blocks (`json ... `).
- Conversational preambles ("Here is the answer: ...").
- Trailing text.
- Malformed JSON (trailing commas, comments).

Simple regex extraction (`{.*}`) is brittle.

## 2. Proposed Solution
Introduce a **Parsing Layer** using a lightweight LLM (Gemini 2.0 Flash or similar) to sanitize output before validation.

### Workflow
1.  **Agent Output:** `Raw Text`
2.  **Validator:** Try `json.loads(Raw Text)`.
3.  **Fallback 1:** Try regex extraction of code blocks.
4.  **Fallback 2 (The New Step):** Call `LLM_Parser`.
    - **Prompt:** "Extract the JSON object matching schema X from the following text. Repair any syntax errors."
    - **Model:** `gemini-2.0-flash-exp` (Low latency, cheap).
    - **Output:** Valid JSON string.

## 3. Architecture
- **Component:** `JsonSanitizer` class in `benchmarks/analysis`.
- **Integration:** Call inside `AdkAnswerGenerator.generate_answer` (as post-processing) OR in the `benchmark_runner` validation phase.
- **Note:** `PostProcessedAdkAnswerGenerator` already does this! We should standardize it for ALL generators, or at least the validation harness.

## 4. Pros/Cons
- **Pros:** Drastically higher pass rate for "Format Errors". Decouples reasoning from formatting.
- **Cons:** Added latency and cost. Risk of the parser hallucinating data to fix the schema.

## 5. Risk Mitigation
- The parser must generally be "extractive" only.
- Monitor "Parser Correction Rate" as a metric. If high, prompt engineering on the Agent is needed.
