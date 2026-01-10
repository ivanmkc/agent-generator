# Agent Verification Criteria & Constraints

All agent architectures and experiments must strictly adhere to the following criteria. Any deviation constitutes a failure, regardless of the benchmark pass rate.

## 1. Zero-Knowledge Prompts (The "Generalization" Rule)
*   **Constraint:** System instructions and prompts **MUST NOT** contain specific information about the target library's API, class names, file paths, or implementation details.
*   **Forbidden Examples:**
    *   "Remember that `BaseAgent` is a Pydantic model."
    *   "Use `google.adk.agents`."
    *   "The context object has a `user_content` attribute."
*   **Allowed Examples:**
    *   "Explore the codebase to understand the base classes."
    *   "Verify the signature of any class you inherit from."
    *   "Follow standard Python best practices."

## 2. Dynamic Discovery
*   **Requirement:** The agent must actively discover API contracts using tools.
*   **Verification:** The trace log must show a logical chain:
    1.  `get_file_tree` -> Locates relevant files.
    2.  `read_definitions` (or equivalent) -> Inspects `BaseAgent` or `LlmAgent`.
    3.  **Inference:** The agent sees `class BaseAgent(BaseModel)` in the tool output and *deduces* that keyword initialization is required. It cannot be told this.

## 3. Token Efficiency
*   **Budget:** < 15,000 prompt tokens per turn.
*   **Constraint:** No massive context injections. No reading entire files unless absolutely necessary.

## 4. Output Compliance
*   **Requirement:** Generated code must strictly follow the user's requested format (e.g., specific wrapper functions like `create_agent`).
*   **Constraint:** This must be achieved via generic instruction (e.g., "Follow the requested template") rather than API-specific templates.

## 5. Clean Environment
*   **Requirement:** Experiments must run in a fresh, isolated environment (Podman container or equivalent venv) to ensure no state leakage.
