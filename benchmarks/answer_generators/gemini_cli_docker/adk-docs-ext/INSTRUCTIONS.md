CONTEXT: You are working in a Docker container equipped with the ADK Documentation Extension. You do NOT have direct access to the source code files on disk.

**MANDATORY RESEARCH PHASE:**
Before generating any code or answering questions:
1.  **Use Documentation Tools:** You MUST use the available extension tools (e.g., `adk-docs-ext`, `search_docs`, `fetch_docs`) to find information about the ADK framework.
2.  **Verify via Docs:** Use the documentation to verify correct imports, class definitions, and function signatures. Do not guess.

## File System Usage

- **Temporary Files:** If you need to create temporary files, **ALWAYS** write them to `/workdir/tmp/`. Do NOT write to `/tmp` or the root of `/workdir` unless strictly necessary.
- **Output:** Write your final solution to the current directory (`/workdir`) or as instructed.
