# ADK Agent Architecture Diagram (ASCII)

This diagram illustrates the current "State-Centric" architecture where agents communicate primarily through the shared `session.state` using specific tools, rather than passing complex JSON objects in their output text.

```
+----------------+
|  User Request  |
+-------+--------+
        |
        v
+-------+--------+
|  Setup Agent   |
+-------+--------+
        |
        v
+-------+--------+
| Prompt Sanitizer|
+-------+--------+
        |
        v
+-------+--------+
|   Use Index?   | (Decision)
+-------+--------+
    /         \
   /           \
  v             v
+-----------------------+   +-----------------------+
|  Knowledge Retrieval  |   |  Knowledge Retrieval  |
|  (Index-Based)        |   |  (Tool-Based / Baseline)|
+-----------+-----------+   +-----------+-----------+
            |                       |
            v                       v
[State: relevant_modules_json]  [State: knowledge_context]
            |                       | (Summarized)
            v                       v
+-----------+-----------+   +-----------------------+
| Knowledge Context     |   |                       |
| Fetcher (Detailed)    |   |                       |
+-----------+-----------+   +-----------------------+
            | (Detailed)
            v
[State: knowledge_context]
            |
            v
+-----------+-----------+
|    Planner Agent      |
+-----------+-----------+
        |
        +-- (Text Plan) --> +---------------------+
        +-- (Tool: save_verification_plan) --> [State: test_prompt]
        |
        v
+---------------------+
|  Candidate Creator  |
+---------------------+
        |
        +-- (Tool: save_agent_code) --> [State: agent_code]
        |
        v
+---------------------+
|  Code-Based Verifier|
+---------------------+
        |    ^
        |    | (Run Agent & Analyze)
        +--->+ [State: test_prompt]
        |    |
        +<---+ [State: agent_code]
        |
        v
[State: verification_result]
        |
        v
+-------+--------+
| Final Verifier |
+-------+--------+
        |
        v
+-------+--------+
| Teardown Agent |
+-------+--------+
        |
        v
+----------------+
|  Final Response|
+----------------+
```

## Component Roles (Simplified):

*   **User Request:** The initial request or problem.
*   **Setup Agent:** Initializes the workspace and captures the raw user request.
*   **Prompt Sanitizer:** Cleans the user request, removing unwanted instructions, and saves it to state.
*   **Use Index? (Decision):** Determines the knowledge retrieval strategy.
*   **Knowledge Retrieval (Index-Based):**
    *   Reads `adk_index.yaml` (fast lookup).
    *   Uses `save_relevant_modules` tool to store a list of modules in `state: relevant_modules_json`.
*   **Knowledge Retrieval (Tool-Based / Baseline):**
    *   Uses LLM with tools (search, read_file, get_module_help) to explore.
    *   Outputs a summarized `state: knowledge_context`.
*   **Knowledge Context Fetcher (Detailed):** (Only for Index-Based)
    *   Reads `state: relevant_modules_json`.
    *   Programmatically fetches full docstrings for selected modules.
    *   Saves detailed docstrings to `state: knowledge_context`.
*   **Planner Agent:**
    *   Receives `state: knowledge_context` and `state: sanitized_user_request`.
    *   Generates an implementation plan (text output to `CandidateCreator`).
    *   Uses `save_verification_plan` tool to store the test prompt in `state: test_prompt`.
*   **Candidate Creator:**
    *   Receives the text plan from `Planner` and `state: verification_result` (if loop).
    *   Implement`s or fixes code.
    *   Uses `save_agent_code` tool to store the generated code in `state: agent_code`.
*   **Code-Based Verifier:**
    *   Reads `state: agent_code` and `state: test_prompt`.
    *   Executes the generated agent code using `run_adk_agent` tool.
    *   Analyzes results and saves `state: verification_result` (success/failure, logs).
*   **Final Verifier:** Persists the final solution (code and rationale).
*   **Teardown Agent:** Cleans up temporary workspace files.
*   **Final Response:** The ultimate output from the benchmark run.
