CONTEXT: You are working in a Docker container. The project source code is located in the directory `/repos/adk-python`. You MUST look into `/workdir/repos/adk-python` to find source files, tests, or configuration. When asked questions about adk-python, you MUST refer to the code in `/workdir/repos/adk-python` to provide answers.

**MANDATORY RESEARCH PHASE:**
Before generating any code or answering questions:
1.  **Consult the Repo:** You MUST use search tools (e.g., `grep`, `find`) to locate relevant classes and functions within `/workdir/repos/adk-python`.
2.  **Search for Unit Tests:** Look in `tests/` for examples of how to correctly instantiate agents and use the API. Unit tests are the source of truth for how to use the API correctly.
3.  **Verify Imports & Signatures:** Do NOT guess imports. Verify the exact module path (e.g., `google.adk.agents.base_agent`) and constructor arguments by reading the source files.

## File System Usage

- The source code is located in `/workdir/repos/adk-python`.
- You are currently in `/workdir`.
- **Temporary Files:** If you need to create temporary files, **ALWAYS** write them to `/workdir/tmp/`. Do NOT write to `/tmp` or the root of `/workdir` unless strictly necessary.
- **Output:** Write your final solution or modified files to their original locations in `/workdir/repos/adk-python` (or wherever instructed).
