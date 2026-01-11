# ADK Agent Debugging & Optimization Report

## 1. Overview & Objectives
**Goal:** Develop a general-purpose ADK agent capable of solving diverse coding benchmarks while strictly minimizing token usage to < 15k tokens per turn.
**Context:** Context injection and global grep strategies were causing token bloat (50k+ tokens), making agents unsustainable for production scaling.

**Constraints & Requirements:**
*   **Low Token Count:** Must stay under 15k prompt tokens (target ~2.5k for base turns).
*   **Zero-Knowledge:** No pre-fetched context in system prompts.
*   **Dynamic Discovery:** Agents must discover API signatures using tools.

## 2. Strategic Architecture

### Design Philosophy
*   **Map & Navigate:** Avoid global greps. Provide a high-level file tree and force the agent to selectively inspect files.
*   **Markovian Workflow:** Isolate context between specialized agents (Discovery -> Plan -> Code) using `include_contents='none'`.
*   **ReAct Protocol:** Strict "Verify-then-Act" loop.

### Core Components
*   **Topology:** The structural arrangement of agents (e.g., Single-Agent ReAct vs. Markovian Chain). Defines how control flows.
*   **Discovery Strategy:** The mechanism for retrieving codebase context (e.g., Context Injection vs. Abstracted Inspection). Balances noise vs. signal.
*   **Memory Model:** The policy for retaining vs. shedding context (e.g., Full History vs. Isolated State). Optimizes for token window efficiency.
*   **Verification Loop:** The protocol for validating outputs (e.g., One-Shot vs. Runtime Feedback). Ensures solution robustness.

## 3. Methodology & Verification Protocol

### Verification Steps

**Step A: Local Execution**
```bash
bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "DEBUG_ADK"
```

**Step B: Global Evaluation**
```bash
bash notebooks/run_benchmarks.sh --suite-filter "fix_errors" --generator-filter "ADK_REACT"
```

**Step C: Debugging & Trace Analysis**
Always use the debugging tool to inspect failures and identify hallucinations or tool misuse:
```bash
python tools/debugging.py --run-dir benchmark_runs/<timestamp> --case "Case Name"
```

**Step D: Success Criteria**
*   [ ] Prompt tokens < 15k per turn.
*   [ ] Passes `create_agent` compliance check.
*   [ ] Pass rate > 50% on `fix_errors` suite.

## 4. Running Log of Experiments

### Phase 1: Context Injection (Exps 1-6)
*   **Action:** Pre-fetched documentation into system prompt.
*   **Result:** **Fail (Efficiency).** 50k+ tokens.

### Phase 2: Naive Tool Use (Exp 7)
*   **Action:** Replaced injection with `search_files` (global grep).
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter debug`
*   **Result:** **Fail (Token Flood).** 45k+ tokens.

### Phase 3: Map & Navigate (Exps 8-10)
*   **Action:** Introduced `get_file_tree` and `read_definitions`.
*   **Result:** **Partial Success.** Tokens dropped to ~10k, but accuracy was poor (<10%).

### Phase 4: Markovian Workflow (Exps 11-14)
*   **Action:** Isolated agent history using `include_contents='none'`.
*   **Result:** **Success (Efficiency).** ~12k total tokens. Accuracy improved but hit Pydantic validation hurdles.

### Phase 5: Single-Agent ReAct Solver (Exps 15-Final)
*   **Action:** Consolidated into a single ReAct loop with `get_module_help`.
*   **Result:** **Success (Quality).** 54.2% pass rate on `fix_errors`.

### Phase 6: Statistical Discovery (Exp 20)
*   **Action:** Tested `ADK_STATISTICAL` which prioritizes API results based on usage frequency.
*   **Result:** **Fail.** 0% Pass Rate on Debug Suite.
*   **Analysis:** Agent failed with `ModuleNotFoundError` due to hallucinated import paths and incorrect method signatures.

### Phase 7: Robust Statistical Discovery (Exp 21)
*   **Action:** 
    1. Improved `get_module_help` to handle Pydantic models (showing required fields).
    2. Mandated parent class verification (signatures/methods) in instructions.
    3. Explicitly warned against hallucinating types (e.g., `Input` vs `InvocationContext`).
*   **Result:** **Success (Draft).** Passes complex custom class implementation benchmarks.

---

## 5. Critical Reflections & Lessons Learned
*   **Successes:** The "Map & Navigate" strategy successfully reduced token usage by 80% while maintaining discovery depth.
*   **Failures:** "Blind" statistical discovery leads to hallucinations if the agent ignores runtime-verified signatures in favor of internal biases.
*   **Insights:** Single-Agent ReAct is more effective than MAS when the task requires tight iterative loops over the same file set.
*   **Tooling:** Using `@tools/debugging.py` is essential for identifying subtle implementation errors like incorrect Pydantic field usage.

## 6. Usage & Artifacts
**File Structure:**
*   `benchmarks/answer_generators/adk_agents.py`: Contains the leading `ADK_REACT` agent definition.

**Final Execution Command:**
```bash
# Run the leading candidate against the full fix_errors suite
bash notebooks/run_benchmarks.sh --suite-filter "fix_errors" --generator-filter "ADK_REACT"
```