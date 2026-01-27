# Design Doc: Fix-Error Benchmark Quality Verifier

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
The `fix_error` benchmark suite consists of coding tasks where an agent must fix broken code to pass a specific `test_file`. Common quality issues include:
- **False Positives:** The "unfixed" code actually passes the test (the task is trivial/broken).
- **Impossible Tasks:** The provided `test_file` is buggy or requires internal knowledge not present in the instructions.
- **Ambiguous Instructions:** The prompt asks for "X" but the test verifies "Y".
- **Environment Drift:** The "fixed" solution no longer works due to library updates (ADK API changes).
- **Solution Leakage:** The "unfixed" code contains the answer in comments or structure, making the task trivial.

## 2. System Architecture

The architecture mirrors the [Question Quality Verifier](./question_quality_verifier.md) but adapts the workflow for code execution cycles rather than multiple-choice logic.

### 2.1 Component Diagram

```text
+-----------------------+       +-------------------------+
|  Benchmark Registry   |       |   Code Execution Sandbox|
| (Fix Error Cases)     |       | (Pytest + VirtualEnv)   |
+-----------+-----------+       +------------+------------+
            |                              ^
            | Load (Unfixed, Test, Prompt) | 1. Run Baseline
            v                              | 2. Run Generated Fix
+-----------+-----------+       +----------+----------+
|    Verification       |       |   Verifier Agent    |
|    Orchestrator       |-----> | **(Gemini-3-Pro-Preview)**|
+-----------+-----------+       +----------+----------+
            |                              |
            | 1. Analyze Requirements      | 1. Read Test Code
            | 2. Prove Failure (Baseline)  | 2. Generate Fix
            | 3. Prove Solvability         | 3. **PROVE via PYTEST**
            | 4. Check for Leakage         | 4. Compare Unfixed vs Fixed
            | <---- Agent's Verdict -------+
            |
            v
+-----------+-----------+
|    Quality Report     |
| (Markdown/JSON Log)   |
+-----------------------+
```

## 3. Workflow Logic: Four-Stage Verification

The verifier must prove four specific claims to validate a `fix_error` case.

```text
[ Start Verification Loop ]
          |
          v
  1. LOAD CASE
     - `unfixed.py` (The Bug)
     - `test_agent.py` (The Validator)
     - `fixed.py` (The Solution)
     - `description` (The Prompt)
          |
          v
  2. CLAIM 1: "The Bug is Real" (Baseline Check)
     - **Action:** Run `pytest test_agent.py` against `unfixed.py`.
     - **Requirement:** MUST FAIL.
     - *If Pass:* Flag as **INVALID (Trivial)**.
          |
          v
  3. CLAIM 2: "The Solution is Secret" (Anti-Leakage Check)
     - **Agent Action:** Compare `unfixed.py` and `fixed.py`.
     - **Logic:** Check for commented-out solutions or overly specific diagnostics.
     - **Requirement:** No trivial leaks.
     - *If Fail:* Flag as **LEAKAGE**.
          |
          v
  4. CLAIM 3: "The Solution is Derivable" (Solvability Check)
     - **Agent Action:** 
         a. Read `description` and `test_agent.py`.
         b. Research ADK docs/codebase (if needed).
         c. Generate `candidate_fix.py`.
     - **Action:** Run `pytest test_agent.py` against `candidate_fix.py`.
     - **Requirement:** MUST PASS.
     - *If Fail:* Flag as **IMPOSSIBLE/AMBIGUOUS**.
          |
          v
  5. CLAIM 4: "Ground Truth is Valid" (Drift Check - Optional)
     - **Action:** Run `pytest test_agent.py` against `fixed.py`.
     - **Requirement:** MUST PASS.
     - *If Fail:* Flag as **BROKEN/OUTDATED**.
          |
          v
  6. VERDICT SYNTHESIS
     - **Valid:** Baseline Fails AND No Leakage AND Candidate Passes.
     - **Broken:** Baseline Passes OR Ground Truth Fails.
     - **Ambiguous:** Agent cannot solve it (Candidate Fails).
```

## 4. Proof Strategies (Detailed)

### 4.1 Proving the Bug (Negative Proof)
*   **Goal:** Ensure the starting state is actually broken.
*   **Execution:** 
    ```bash
    cp unfixed.py agent.py
    pytest test_agent.py
    ```
*   **Assertion:** `Exit Code != 0`.

### 4.2 Proving Anti-Leakage
*   **Goal:** Ensure the problem isn't trivialized by leaking the answer.
*   **Agent Logic:** "You are a stricter exam proctor. Review `unfixed.py`. Does it contain:
    1.  The exact solution commented out?
    2.  Comments explicitly stating the fix (e.g., 'Change X to Y') rather than the error?
    3.  Structure that makes the fix a trivial fill-in-the-blank (unless intended)?"

### 4.3 Proving Solvability (Positive Proof)
*   **Goal:** Ensure an intelligent agent can solve it using *only* the instructions and public API.
*   **Execution:**
    1.  **Analyst Agent:** Reads `test_agent.py` to understand the assertions.
    2.  **Coder Agent:** Writes `candidate.py`.
    3.  **Runner:** 
        ```bash
        cp candidate.py agent.py
        pytest test_agent.py
        ```
*   **Assertion:** `Exit Code == 0`.

## 5. Implementation Plan

### Phase 1: The Verifier Agents

We use a split architecture:

1.  **Test Analyst (LlmAgent):**
    *   **Input:** `test_agent.py` content, `description`.
    *   **Task:** "Explain what this test requires. What must the agent do to pass?"
    *   **Output:** Implementation Plan.

2.  **Proctor Agent (LlmAgent - Anti-Leakage):**
    *   **Input:** `unfixed.py`, `fixed.py`.
    *   **Task:** Detect solution leakage.
    *   **Output:** `LeakageReport`.

3.  **Solution Engineer (LlmAgent):**
    *   **Input:** Implementation Plan.
    *   **Task:** Write the Python code for `agent.py`.
    *   **Output:** Code block.

4.  **Execution Harness (Tool):**
    *   **Task:** Setup temp dir, write files, run pytest, capture stdout.

### Phase 2: Remediation Loop (Fixer)

If the **Solvability Check** fails (Agent can't fix it):
1.  **Diagnose:** Compare `test_failure_output` vs `description`.
2.  **Fix Strategy:** Update Prompt or Test.
3.  **Action:** Generate patched files.
4.  **Loop:** Re-run verification.

## 6. ADK Implementation Logic

```text
+-----------------------------------------------------------------------+
|  SequentialAgent: "fix_error_verifier"                                |
|                                                                       |
|  1. [SetupAgent]                                                      |
|     - Create isolated tmp env.                                        |
|                                                                       |
|  2. [ToolAgent] "baseline_check"                                      |
|     - Action: Run pytest on `unfixed.py`.                             |
|     - Logic: If PASS, throw "BenchmarkInvalidError".                  |
|                                                                       |
|  3. [LlmAgent] "proctor" (Leakage Check)                              |
|     - Input: unfixed.py vs fixed.py.                                  |
|     - Output: Pass/Fail.                                              |
|                                                                       |
|  4. [LlmAgent] "analyst"                                              |
|     - Input: Test code + Instructions.                                |
|     - Output: "Requirements List".                                    |
|                                                                       |
|  5. [LoopAgent] "solver_loop" (Max 3 attempts)                        |
|     - [LlmAgent] "coder": Writes `agent.py`.                          |
|     - [ToolAgent] "tester": Runs pytest.                              |
|     - [LlmAgent] "debugger": Reads error, adjusts code (if needed).   |
|                                                                       |
|  6. [LlmAgent] "verdict"                                              |
|     - If solver succeeded: VERDICT = VALID.                           |
|     - If solver failed: VERDICT = IMPOSSIBLE/AMBIGUOUS.               |
+-----------------------------------------------------------------------+
```