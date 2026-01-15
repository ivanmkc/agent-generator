# Prismatic Benchmark Generator Plan

## Goal
Create a high-quality, diverse benchmark suite for the ADK (Agent Development Kit) Python framework. The suite will contain two types of Multiple Choice Questions (MCQs):
1.  **Execution MCQs:** Based on valid code execution traces (Golden Snapshots) and adversarial mutants.
2.  **Conceptual MCQs:** Based on semantic analysis of class/function responsibilities, testing understanding of *what* a component does rather than just *how* to call it.

## Architecture
- **Coordinator (Auditor):** Uses `gemini-2.0-flash-exp` (via injection) to scan the repo and prioritize targets.
- **Worker Pipeline:**
    - **Execution Mode:** Observer -> Saboteur -> Referee -> Critic -> Assembler.
    - **Concept Mode:** Analyst -> Confabulator -> Reviewer -> Assembler.
- **Infrastructure:**
    - **Isolation:** Agents use `include_contents='none'` to prevent history pollution.
    - **Persistence:** State is saved to `processed_targets.json` to allow resumption.
    - **Injection:** Models are fully injected from the CLI (`run_generator.py`).

## Status

### Phase 1: Execution MCQ Pipeline (COMPLETE)
- [x] **Core Logic:** Implemented `Observer` (Trace), `Saboteur` (Mutate), `Referee` (Validate).
- [x] **Optimization:** Using `gemini-2.0-flash-exp` for Auditor and `gemini-3-pro-preview` for Worker.
- [x] **Refactoring:** Removed hardcoded defaults; enforced strict dependency injection for models.
- [x] **Verification:** Verified end-to-end generation of Execution MCQs.

### Phase 2: Conceptual MCQ Pipeline (NEXT)
- [ ] **Task:** Generate Conceptual MCQs using `mode="concept_mcq"`.
- [ ] **Analyst Agent:** Summarizes the primary responsibility of a target (Truth).
- [ ] **Confabulator Agent:** Generates plausible but incorrect descriptions (Distractors).
- [ ] **Reviewer Agent:** Validates that distractors are distinct from the truth.
- [ ] **Assembler Agent:** Formats the final JSON.

## Backlog
- [ ] **Scale Up:** Run the generator on the full ADK codebase to create a comprehensive suite (target ~50-100 questions).
- [ ] **Human Review:** Manually spot-check a sample of generated benchmarks for quality.
