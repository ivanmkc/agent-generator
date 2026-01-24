# Design Doc: Benchmark Question Quality Verifier

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
The benchmark suite contains questions that are:
- **Ambiguous:** Multiple valid answers.
- **Outdated:** Referencing deprecated APIs.
- **Incorrect:** The "Ground Truth" contradicts the actual codebase.

Manual review is slow.

## 2. Proposed Solution
Create an automated **Verifier Agent** that audits benchmark cases.

### Architecture
- **Agent:** `AdkKnowledgeAgent` (High capability, access to `inspect_fqn`, `search`).
- **Input:** A benchmark case (Question + Options + Ground Truth).
- **Task:**
    1.  Research the question independently.
    2.  Determine the answer.
    3.  Compare with Ground Truth.
    4.  **Critique:** Is the question clear? Is the Ground Truth correct? Are distractor options plausible?

### Workflow
1.  Load all benchmarks.
2.  For each case:
    - Run Verifier Agent.
    - If `Verifier Answer != Ground Truth`: Flag for human review.
    - If `Verifier Critique` mentions "Ambiguous": Flag.

## 3. Output
A `quality_report.md` listing:
- **Suspicious Cases:** Questions where the agent strongly disagrees with the ground truth.
- **Ambiguous Cases:** Questions where the agent found multiple plausible interpretations.

## 4. Implementation
- Reuse `benchmarks/answer_generators/adk_agent_runner.py`.
- New script: `tools/verify_benchmarks.py`.
