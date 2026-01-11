# Comparison: Gemini CLI vs. ADK Agents (Code Writing)

## Overview

This report compares the code writing workflows, tools, and strategies of the `gemini-cli` repository against our current ADK-based agents (`StructuredWorkflowAdk`).

## 1. Tools

| Feature | Gemini CLI (`EditTool`, `WriteFileTool`) | ADK Agents (`AdkTools.write_file`) |
| :--- | :--- | :--- |
| **Partial Edits** | **Supported** (`EditTool`). Uses `old_string` / `new_string` for precise search-and-replace. | **Not Supported.** Agents must rewrite the entire file using `write_file`. |
| **Verification** | **Strict.** `EditTool` verifies occurrence count and exact string match before applying. | **None.** `write_file` blindly overwrites. |
| **User Confirmation** | **Interactive.** Calculates and displays a `diff` (patch) for user approval before execution. Supports IDE integration. | **None / Implicit.** Agents execute changes autonomously; verification happens via subsequent test runs. |
| **Safety** | **High.** `safeLiteralReplace` handles special chars. Errors if target string not found or ambiguous. | **Low.** Risk of hallucinated content or wiping file accidentally if agent context is incomplete. |
| **New Files** | Explicit logic in `EditTool` (empty `old_string`) or `WriteFileTool`. | `write_file` handles creation and overwrite indistinguishably. |

## 2. Workflow & Steps

### Gemini CLI (Interactive Assistant)
1.  **Read:** Agent reads file to understand context.
2.  **Propose:** Agent calls `edit` with `old_string` and `new_string`.
3.  **Validate (System):** System checks if `old_string` exists and is unique. If not, it errors *before* touching the file.
4.  **Confirm (User):** System generates a diff. User (developer) reviews and approves.
5.  **Apply:** Change is written to disk.

### ADK Agents (Autonomous Loop)
1.  **Retrieval:** `module_selector_agent` / `docstring_fetcher_agent` gather context.
2.  **Plan:** `implementation_planner` creates a plan.
3.  **Implement:** `candidate_creator` receives the plan and **rewrites the entire target file** using `write_file`.
4.  **Verify:** `code_based_runner` executes the code/tests. `run_analysis_agent` reviews logs.
5.  **Loop:** If verification fails, `run_analysis_agent` provides feedback, and `candidate_creator` rewrites the file again.

## 3. Key Differences

1.  **Granularity:** Gemini CLI operates on *diffs/patches*, minimizing context usage and token generation for small changes. ADK agents operate on *whole files*, which is token-expensive and prone to "forgetting" parts of the file if the context window is tight.
2.  **Human-in-the-Loop:** Gemini CLI is designed for collaboration (propose -> confirm -> apply). ADK agents are designed for autonomy (plan -> execute -> verify -> loop).
3.  **Error Handling:** Gemini CLI fails fast if the "anchor" text (`old_string`) is invalid. ADK agents might silently introduce regression bugs by rewriting a file incorrectly, only catching them if a test case covers it.

## 4. Recommendations for ADK Agents

To improve the ADK agents' reliability and efficiency, we should adopt:

1.  **`Replace` Tool:** Implement a tool similar to `EditTool` that allows replacing specific blocks of code. This drastically reduces "Output Token" usage compared to rewriting full files.
2.  **Diff-Based Feedback:** When an agent rewrites a file, the system could generate a diff and feed it back to the `run_analysis_agent` or the next iteration, helping the model "see" what it changed.
3.  **Anchor Validation:** If we implement `replace`, strictly enforce that `old_string` must match existing content exactly. This acts as a grounding mechanism, reducing hallucinations.
