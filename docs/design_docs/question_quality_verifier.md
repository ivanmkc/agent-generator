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
|    Orchestrator       |-----> | (Gemini-3-Pro-Preview)|
+-----------+-----------+       +----------+----------+
            |                              |
            | 1. Provide Question          | 1. Research (search/inspect)
            | 2. Provide Options           | 2. Decompose Claims
            |                              | 3. **PROVE via CODE** (All Claims)
            | <---- Agent's Verdict -------+
            |
            v
+-----------+-----------+
|    Quality Report     |
| (Markdown/JSON Log)   |
+-----------------------+
```

### 2.2 The Verifier Agent
The agent is configured as a "Codebase Researcher & Tester" with the following tools:
- **Research:** `search_ranked_targets`, `inspect_fqn`, `read_file`.
- **Execution:** `write_file`, `run_shell_command` (or `run_adk_agent`/`pytest`).

**System Instruction:**
> "You are a Senior QA Engineer auditing a certification exam for the Google ADK. Your goal is to verify if a question is fair, accurate, and unambiguous. You MUST NOT rely on your internal knowledge. You MUST **prove** every claim (positive or negative) by writing and executing a Python test script against the installed library."

## 3. Workflow Logic: Claim Decomposition & Verification

The verification process follows a strict "Decompose -> Verify -> Verdict" loop. No confidence scalars are used; verification is binary (Proven/Disproven).

```text
[ Start Verification Loop ]
          |
          v
  1. LOAD CASE (Question + Options)
     *Do not reveal Ground Truth to Agent yet.*
          |
          v
  2. CLAIM DECOMPOSITION
     - The Agent breaks down the Question and EACH Option into atomic claims.
     - Example (Option A): "EventsCompactionConfig accepts 'interval' arg." -> Claim: True
     - Example (Option B): "EventsCompactionConfig accepts 'freq' arg." -> Claim: False
          |
          v
  3. **EMPIRICAL VERIFICATION (The "Proof" Phase)**
     - **Constraint:** EVERY Claim must have a corresponding Python script.
     - Script A: `try: EventsCompactionConfig(interval=5); print('PASS') except: print('FAIL')`
     - Script B: `try: EventsCompactionConfig(freq=5); print('UNEXPECTED PASS') except ValidationError: print('EXPECTED FAIL')`
          |
          v
  4. VERDICT SYNTHESIS
     - **Valid Question:**
       - Correct Option: Script PASSED (Proving it works).
       - Distractor Options: Scripts FAILED (Proving they are invalid).
     - **Ambiguous Question:**
       - Multiple Options PASSED.
     - **Incorrect Question:**
       - Correct Option FAILED (or behavior didn't match).
          |
          v
  5. REPORT GENERATION
```

## 4. Proof Strategies (Detailed)

The agent must rigorously prove why an option is Correct or Incorrect.

### 4.1 Proving "True" Statements
If Option A says *"Use `compaction_interval` to configure summarization frequency"*:
*   **Action:** Write a script that initializes `EventsCompactionConfig(compaction_interval=5)`.
*   **Verification:** Assert no `ValidationError` is raised and the property is set.

### 4.2 Proving "False" Statements (Negative Proof)
If Option B says *"Use `summarization_freq` to configure..."* (a non-existent field):
*   **Action:** Write a script attempting `EventsCompactionConfig(summarization_freq=5)`.
*   **Verification:** Assert that `ValidationError` ("Extra inputs not permitted") IS raised.
    *   *Crucial:* If the script *runs without error*, Option B is actually Valid, making the question ambiguous!

### 4.3 Proving Runtime Behavior
If the question asks *"What happens if you run X?"*:
*   **Action:** Write a script that actually runs X (using mocks if necessary for network calls).
*   **Verification:** Capture stdout/stderr or return values and assert they match the option description.

## 5. Implementation Plan

### Phase 1: The `verify_benchmarks.py` Tool
- **Script:** A CLI tool to iterate over `benchmarks/benchmark_definitions/*.yaml`.
- **Runner:** Instantiates `AdkAnswerGenerator` with the `VerifierAgent` config.
- **Output:** Generates `quality_report.json` and a human-readable `quality_audit.md`.

### Phase 2: The Verifier Agent Prompt
We need a specialized prompt that forces the model to cite *evidence*.

**Draft Prompt:**
```text
Task: Audit this Multiple Choice Question.

Question: {question}
Options: {options}

STEP 1: Research. Find relevant classes/methods.

STEP 2: Decompose & Prove.
For EACH option (A, B, C, D...):
1. State the implicit claim (e.g., "This code runs without error", "This arg exists").
2. Write a self-contained Python script to TEST that claim.
3. Execute the script.
4. Record the result.

STEP 3: Evaluate.
- Did the "Correct" option script succeed?
- Did the "Distractor" option scripts fail (as expected)?
- If a Distractor succeeded, the question is AMBIGUOUS.

Output JSON: {
  "option_proofs": {
    "A": {"claim": "...", "status": "Proven Valid"},
    "B": {"claim": "...", "status": "Proven Invalid (Error: ...)"}
  },
  "quality_rating": "Valid" | "Ambiguous" | "Incorrect",
  "critique": "..."
}
```

### Phase 3: Integration
- Add a CI/CD step (weekly) to run the verifier on the `main` branch to catch drift (e.g., when ADK version bumps).