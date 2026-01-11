# [Task Name] Development Log

## 1. Overview & Objectives
**Goal:** [One sentence summary of the primary objective]
**Context:** [Why is this needed? What problem does it solve?]

**Constraints & Requirements:**
*   [Constraint 1]
*   [Constraint 2]

## 2. Strategic Architecture
*Describe the high-level design decisions and the "theory" behind them.*

### Design Philosophy
*   **Principle A:** [Description]
*   **Principle B:** [Description]

### Core Components
*   **[Component 1]:** [Role and Responsibility]
*   **[Component 2]:** [Role and Responsibility]

## 3. Methodology & Verification Protocol
**CRITICAL:** Every verification step MUST include the exact shell command required to execute it. 
**Strict Protocol:** You MUST run the relevant verification step after *every* iteration or significant code change. Do not proceed until verification passes or the failure is understood.

### Verification Steps

**Step A: Unit Testing**
```bash
# MANDATORY: exact command to run unit tests
# Example: env/bin/python -m pytest path/to/test.py
```

**Step B: Integration/E2E Testing**
```bash
# MANDATORY: exact command to run the full system trial
# Include all necessary environment variables or path prefixes.
# Example: PYTHONPATH=. env/bin/python path/to/script.py --arg value
```

**Step C: Success Criteria**
*   [ ] Criterion 1
*   [ ] Criterion 2

## 4. Running Log of Experiments
**Location:** Store detailed logs in `ai_instructions/experiments/<task_name>/exp_NN_[name].md`.

**Standardized Iteration Loop:**
1.  **Hypothesis:** Define what you expect to happen.
2.  **Implementation:** Make the minimal necessary change.
3.  **Verification:** Run the *exact* command from Section 3.
4.  **Analysis:** If it failed, *why*? (Check logs/traces).
5.  **Pivot:** Decide the next step (Fix, Revert, or New Strategy).

**Instruction:** Follow this cycle for every experiment:
1.  **Define Hypothesis:** What do you expect to happen?
2.  **Execute & Log:** Run the command and record it exactly.
3.  **Record Result:** Pass, Fail, or Partial.
4.  **Analyze (RCA):** If it failed, *why*? If it passed, *how*?
5.  **Pivot:** What is the next step based on this result?

### Phase 1: [Phase Name] (Attempts X-Y)
*   **Action:** [What did you build?]
*   **Command:** `[The exact command run during this phase]`
*   **Hypothesis:** [What did you expect?]
*   **Result:** [Pass/Fail/Partial]
*   **RCA (Root Cause Analysis):** [Why did it fail/succeed?]
*   **Pivot:** [How did you adjust the strategy?]

### Phase 2: [Phase Name] (Attempts Z-...)
*   **Action:** ...

---

## 5. Critical Reflections & Lessons Learned
*   **Successes:** What worked well?
*   **Failures:** What dead-ends were encountered?
*   **Insights:** Generalizable learnings for future tasks.

## 6. Usage & Artifacts
**File Structure:**
*   `path/to/file.py`: Description

**Final Execution Command:**
```bash
# MANDATORY: Provide the definitive command to run the final solution.
# Include example arguments and expected output descriptions.
```

**Helper Scripts:**
*List any auxiliary scripts used for data migration, cleanup, or specialized verification.*

## 7. Appendix: Comprehensive Experiment Log
*Summarize all experiments in a table for quick reference.*

| ID | Experiment Name | Command / Config | Result | Key Finding |
| :--- | :--- | :--- | :--- | :--- |
| **Exp 1** | [Name] | `[Command]` | [Pass/Fail] | [One-sentence insight] |
| **Exp 2** | ... | ... | ... | ... |