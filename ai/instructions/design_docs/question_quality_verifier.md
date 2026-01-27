# Design Doc: Benchmark Question Quality Verifier

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
The benchmark suite, particularly `multiple_choice` and `api_understanding` cases, suffers from data quality issues such as:
- **Ambiguity:** Questions with multiple technically correct answers or poor phrasing.
- **Drift:** "Ground Truth" answers that contradict the current ADK codebase (v1.20+) due to API changes.
- **Flawed Distractors:** Options that are too obviously wrong or confusingly similar.

Manual review of hundreds of cases is inefficient. We need an automated system to "grade the graders" that relies on **empirical evidence**, not just LLM reasoning.

## 2. System Architecture

The solution uses a specialized **Verifier Agent**—a high-capability LLM agent equipped with deep introspection *and* code execution tools—to independently solve each benchmark case and prove its verdict.

### 2.1 Component Diagram

```text
+-----------------------+       +-------------------------+
|   Benchmark Registry  |       |   ADK Runtime Environment|
| (YAML/JSON Definitions)|       |  (Live Codebase v1.20+) |
+-----------+-----------+       +------------+------------+
            |                              ^
            | Load Case                    | 1. Introspect
            v                              | 2. Execute Tests
+-----------+-----------+       +----------+----------+
|    Verification       |       |   Verifier Agent    |
|    Orchestrator       |-----> | **(Gemini-3-Pro-Preview)**|
+-----------+-----------+       +----------+----------+
            |                              |
            | 1. Provide Question          | 1. Research (search/inspect)
            | 2. Provide Options           | 2. Decompose Claims (Analyst)
            |                              | 3. **PROVE via PYTEST** (Engineer)
            | <---- Agent's Verdict -------+
            |
            v
+-----------+-----------+
|    Quality Report     |
| (Markdown/JSON Log)   |
+-----------------------+
```

### 2.2 The Verifier Agent Pair
The verification task is split between two specialized sub-agents:

1.  **Claim Analyst (LlmAgent):**
    *   **Goal:** Research the codebase and decompose the question into atomic, testable claims.
    *   **Tools:** `search_ranked_targets`, `inspect_fqn`.
    *   **Output:** A list of `VerificationTask` objects (one per option) to `session.state`.

2.  **Proof Engineer (LoopAgent):**
    *   **Goal:** Rigorously prove each claim by writing and running code.
    *   **Tools:** `write_file`, `run_shell_command` (pytest), `read_file`.
    *   **Input:** Reads `VerificationTask` list from `session.state`.

**System Instruction (Shared):**
> "You are a Senior QA Engineer auditing a certification exam. You must NOT rely on internal knowledge. You must PROVE every claim (positive or negative) by writing and executing `pytest` scripts against the installed library."

## 3. Workflow Logic: Claim Decomposition & Verification

The verification process follows a strict "Decompose -> Verify -> Verdict" loop.

```text
[ Start Verification Loop ]
          |
          v
  1. LOAD CASE (Question + Options)
     *Do not reveal Ground Truth to Agent yet.*
          |
          v
  2. CLAIM DECOMPOSITION (Agent 1: Analyst)
     - Research the relevant classes/methods.
     - Break down EACH Option into a specific hypothesis.
     - Save to State: `claims = [{"option": "A", "type": "positive", "claim": "..."}, ...]`
          |
          v
  3. **EMPIRICAL VERIFICATION (Agent 2: Engineer)**
     - **Constraint:** Loop through `claims`. For each:
       a. Write a `pytest` file (e.g., `test_option_A.py`).
       b. Execute it.
       c. Record result: `Proven Valid` or `Proven Invalid`.
     - *Distractor Logic:* A distractor is "Proven" if the test passes by asserting the expected failure (e.g., `with pytest.raises`).
          |
          v
  4. VERDICT SYNTHESIS
     - **Valid Question:**
       - Correct Option: Script PASSED.
       - Distractor Options: Scripts PASSED (Confirming invalidity).
     - **Ambiguous Question:**
       - Multiple options correspond to "working" code (i.e., distractors failed to fail).
     - **Incorrect Question:**
       - The "Correct" option fails its test.
          |
          v
  5. REPORT GENERATION
```

## 4. Remediation Workflow (The Fix Loop)

If the Verifier flags a question as **Ambiguous** or **Incorrect**, the system enters a remediation cycle.

```text
[ Verdict: Incorrect / Ambiguous ]
          |
          v
  1. FIXER AGENT (Remediation Engineer)
     - Input: Original Question, Verifier's Critique, Proof Results (stdout/stderr).
     - Task: Propose a correction to the YAML/JSON definition.
       - *Drift:* Update the Ground Truth to match current API.
       - *Ambiguity:* Reword the question or harden distractors to be strictly false.
     - Action: `update_benchmark_case(new_definition)`.
          |
          v
  2. RE-VERIFICATION
     - Clear `session.state.results`.
     - Rerun the "Claim Decomposition" & "Empirical Verification" steps on the NEW definition.
          |
          v
  3. CHECK VERDICT
     - If Valid -> **COMMIT** fix.
     - If Still Failed -> Increment Retry Count.
     - Max Retries (e.g., 3) -> Flag for Human Review.
```

## 5. Proof Strategies (Detailed)

The agent must rigorously prove claims using `pytest` assertions.

### 5.1 Proving "True" Statements (Positive Assertion)
If Option A says *"Use `compaction_interval` to configure summarization frequency"*:
*   **Action:** Write `test_option_A.py`.
*   **Code Pattern:**
    ```python
    def test_option_A_validity():
        config = EventsCompactionConfig(compaction_interval=5)
        assert config.compaction_interval == 5, "Property should be set"
    ```
*   **Verification:** Run `pytest test_option_A.py`. Must PASS.

### 5.2 Proving "False" Statements (Negative Assertion)
If Option B says *"Use `summarization_freq` to configure..."* (a non-existent field), this is a "False" claim that acts as a distractor.
*   **Action:** Write `test_option_B.py` to prove it IS invalid.
*   **Code Pattern:**
    ```python
    import pytest
    from pydantic import ValidationError
    def test_option_B_invalidity():
        # Distractor claims this works; we must prove it DOES NOT work.
        # This test PASSES if the code raises the expected error.
        with pytest.raises(ValidationError, match="Extra inputs not permitted"):
            EventsCompactionConfig(summarization_freq=5)
    ```
*   **Verification:** Run `pytest test_option_B.py`. Must PASS (proving the exception occurred).
    *   *Crucial:* If this test FAILS (i.e., the code ran without error), then Option B is actually VALID, and the question is ambiguous!

## 6. Implementation Plan

### Phase 1: The `verify_benchmarks.py` Tool
- **Script:** A CLI tool to iterate over `benchmarks/benchmark_definitions/*.yaml`.
- **Runner:** Instantiates `AdkAnswerGenerator` with the `VerifierAgent` config.
- **Output:** Generates `quality_report.json`.

### Phase 2: Agent Configuration
Use `MOST_POWERFUL_MODEL` (`gemini-3-pro-preview`).

**Analyst Prompt:**
```text
Task: Analyze this Multiple Choice Question.
Question: {question}
Options: {options}

1. Research codebase using `search_ranked_targets` / `inspect_fqn`.
2. For each option, determine the implied claim (e.g., "This code runs", "This raises ValueError").
3. Save a list of `VerificationTask` objects to `session.state.claims`.
   Format: {"option": "A", "hypothesis": "Should run successfully", "code_snippet_hint": "..."}
```

**Engineer Prompt:**
```text
Task: Execute Verification Plan.
Context: You have a list of claims in `session.state.claims`.

1. Iterate through each claim.
2. Write a `pytest` file (`test_option_{letter}.py`).
   - If hypothesis is "Success", assert True.
   - If hypothesis is "Failure" (Distractor), assert Exception (using pytest.raises).
3. Run `pytest`.
4. Record the result in `session.state.results`.
```

### Phase 3: Integration
- Add a CI/CD step (weekly) to run the verifier on the `main` branch to catch drift (e.g., when ADK version bumps).

## 7. Environment Isolation & Dependencies

Executing dynamic verification scripts carries risks of state pollution.

### 7.1 Sandbox Isolation
- **Per-Task VirtualEnv:** Each verification run operates in a clean environment.
- **Temp Directory:** The `verifier_agent` writes `test_*.py` files to `/tmp/adk_verify_<uuid>`.
- **Cleanup:** `CodeBasedTeardownAgent` removes these directories.

### 7.2 Handling Imports
- **PYTHONPATH:** The runner script ensures `PYTHONPATH` includes the local `adk-python` source.
- **Mocking:** Tests must use `unittest.mock` for external services (e.g., Gemini API) to ensure determinism.

## 8. ADK Implementation Logic

The workflow uses nested `LoopAgent`s to handle both verification and remediation.

```text
+-----------------------------------------------------------------------+
|  LoopAgent: "remediation_loop" (Outer Loop)                           |
|  - Max Iterations: 3 (Verdict=Valid breaks loop)                      |
|                                                                       |
|  1. SequentialAgent: "verification_pipeline"                          |
|     a. [SetupAgent]                                                   |
|        - Create tmp dir.                                              |
|                                                                       |
|     b. [LlmAgent] "claim_analyst"                                     |
|        - Input: Current Question Definition.                          |
|        - Output: Claims List.                                         |
|                                                                       |
|     c. [LoopAgent] "proof_engineer_loop"                              |
|        - Sub-Agent: [LlmAgent] "proof_engineer"                       |
|          - Logic: Write Test -> Run Pytest -> Record Result.          |
|                                                                       |
|     d. [LlmAgent] "verdict_synthesizer"                               |
|        - Input: Proof Results vs Ground Truth.                        |
|        - Logic: Determine if Valid, Ambiguous, or Incorrect.          |
|        - Output: `verdict` object.                                    |
|                                                                       |
|  2. [ConditionalAgent] "fix_handler"                                  |
|     - Condition: If verdict != Valid.                                 |
|     - Agent: [LlmAgent] "remediation_engineer"                        |
|       - Input: Critique + Proof Logs.                                 |
|       - Action: `update_benchmark_case(...)`.                         |
|                                                                       |
|  3. [CodeBasedTeardownAgent]                                          |
|     - Delete tmp dir (cleanup after each pass).                       |
+-----------------------------------------------------------------------+
```
