# Design Doc: Benchmark Question Quality Verifier

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
The benchmark suite, particularly `multiple_choice` and `api_understanding` cases, suffers from data quality issues such as:
- **Ambiguity:** Questions with multiple technically correct answers or poor phrasing.
- **Drift:** "Ground Truth" answers that contradict the current ADK codebase (v1.20+) due to API changes.
- **Flawed Distractors:** Options that are too obviously wrong or confusingly similar.

Manual review of hundreds of cases is inefficient. We need an automated system to "grade the graders."

## 2. System Architecture

The solution uses a specialized **Verifier Agent**—a high-capability LLM agent equipped with deep introspection tools—to independently solve each benchmark case and critique its quality.

### 2.1 Component Diagram

```text
+-----------------------+       +-------------------------+
|   Benchmark Registry  |       |   ADK Runtime Environment|
| (YAML/JSON Definitions)|       |  (Live Codebase v1.20+) |
+-----------+-----------+       +------------+------------+
            |                              ^
            | Load Case                    | Introspect
            v                              |
+-----------+-----------+       +----------+----------+
|    Verification       |       |   Verifier Agent    |
|    Orchestrator       |-----> | (Gemini-3-Pro-Preview)|
+-----------+-----------+       +----------+----------+
            |                              |
            | 1. Provide Question          | 1. Research (search/inspect)
            | 2. Provide Options           | 2. Formulate Answer
            |                              | 3. Critique Distractors
            | <---- Agent's Verdict -------+
            |
            v
+-----------+-----------+
|    Quality Report     |
| (Markdown/JSON Log)   |
+-----------------------+
```

### 2.2 The Verifier Agent
The agent is configured as a "Codebase Researcher" with the following tools:
- `search_ranked_targets`: To find relevant classes/methods.
- `inspect_fqn`: To retrieve the *exact* current docstrings and signatures.
- `read_file`: To examine implementation details if docstrings are insufficient.

**System Instruction:**
> "You are a Senior QA Engineer auditing a certification exam for the Google ADK. Your goal is to verify if a question is fair, accurate, and unambiguous based *strictly* on the current codebase."

## 3. Workflow Logic

The verification process follows a strict "Blind Solve -> Critique" loop to avoid bias.

```text
[ Start Verification Loop ]
          |
          v
  1. LOAD CASE (Question + Options)
     *Do not reveal Ground Truth to Agent yet.*
          |
          v
  2. AGENT SOLVE
     - Agent searches codebase.
     - Agent selects its own answer (e.g., "C").
     - Agent provides 'Confidence Score' (0.0 - 1.0).
          |
          v
  3. COMPARISON
     - Orchestrator compares Agent Answer vs. Ground Truth.
          |
     +----+------------------------+
     | Match?                      | No Match?
     v                             v
  [Review Logic]             4. RE-EVALUATION PROMPT
  - If Confidence < 0.9      - "You selected C, but the test says B.
    Flag as 'Ambiguous'         Please investigate B. Is B also valid?
                                Is the test wrong, or did you miss something?"
          |                             |
          v                             v
  5. FINAL VERDICT               5. FINAL VERDICT
     - "Pass"                       - "Disagreement" (Test likely wrong)
     - "Ambiguous"                  - "Ambiguous" (Both valid)
          |                             |
          +------------+----------------+
                       |
                       v
              [ Append to Report ]
```

## 4. Evaluation Criteria

The Orchestrator classifies each case into one of four buckets:

| Status | Description | Action Required |
| :--- | :--- | :--- |
| **✅ Valid** | Agent agrees with Ground Truth (High Confidence). | None. |
| **⚠️ Ambiguous** | Agent agrees but notes confusing phrasing or multiple plausible interpretations. | **Reword Question.** |
| **❌ Incorrect** | Agent proves Ground Truth is factually wrong based on current code (e.g., deprecated param). | **Fix Ground Truth.** |
| **❓ Weak** | Agent answered correctly but found the question trivial or distractors illogical. | **Harden Distractors.** |

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

1. Research the codebase using your tools.
2. Identify the ONE strictly correct answer.
3. If multiple options could be correct, explain why.
4. If no options are correct, explain why.
5. Rate the question quality (Clear, Ambiguous, Incorrect).

Output JSON: {
  "selected_answer": "A",
  "evidence": "File X line Y says...",
  "quality_rating": "Ambiguous",
  "critique": "Option A is correct, but B is arguably true in edge case Z..."
}
```

### Phase 3: Integration
- Add a CI/CD step (weekly) to run the verifier on the `main` branch to catch drift (e.g., when ADK version bumps).