# Context Reduction Strategies in Gemini CLI

## Findings

The `gemini-cli` repository implements several robust strategies for managing context size, particularly when handling file content. These are primarily located in `packages/core/src/tools/read-file.ts` and `packages/core/src/utils/fileUtils.ts`.

### 1. Default and Hard Limits
- **Line Count:** A default limit of **2000 lines** is applied to text file reads (`DEFAULT_MAX_LINES_TEXT_FILE`). This prevents accidental ingestion of massive log files or data dumps.
- **Line Width:** Individual lines are truncated at **2000 characters** (`MAX_LINE_LENGTH_TEXT_FILE`). This protects against minified code or data files with extremely long lines.

### 2. Pagination and Truncation Feedback
- When a file is truncated, the tool injects a structured **warning message** directly into the LLM content:
  ```text
  IMPORTANT: The file content has been truncated.
  Status: Showing lines {start}-{end} of {total} total lines.
  Action: To read more... use offset: {nextOffset}.
  ```
- This "active guidance" teaches the model how to paginate, preventing it from hallucinating the missing content or getting stuck.

### 3. Binary & BOM Protection
- **BOM Detection:** It intelligently detects Byte Order Marks (UTF-8/16/32) to correctly decode text files, avoiding "garbage" characters.
- **Binary Heuristics:** It checks for null bytes and non-printable character ratios (>30%) to identify binary files and strictly prevents reading them as text. This saves tokens and prevents model confusion.

### 4. Separate User vs. LLM Displays
- The system distinguishes between `llmContent` (what the model sees) and `returnDisplay` (what the user sees). This separation allows for verbose context for the model (like the truncation warning) without cluttering the user interface, or conversely, concise summaries for the user while the model gets data.

## Recommendations for Agent Generator

Based on these findings, we can improve our `AdkTools` implementation:

1.  **Implement Line Width Limiting:** We currently limit line *count* (500), but not line *width*. We should add a `cut` or Python slicing to limit lines to ~500-1000 chars to handle minified files.
2.  **Adopt the Structured Warning:** Our current truncation message is good, but adopting the exact "Status/Action" format from Gemini CLI might improve model compliance for pagination.
3.  **Add Binary Detection:** We rely on `UnicodeDecodeError` or `grep` behavior. Implementing a robust binary check (like checking for null bytes) would prevent accidental reads of binary assets.
4.  **Pagination Guidance:** Ensure our `read_file` tool docstring explicitly explains the pagination mechanism as clearly as the Gemini CLI prompt does.

## Action Plan

1.  Update `read_file` in `adk_tools.py` to include line width truncation (max 1000 chars).
2.  Add a basic binary check (if not UTF-8 decodeable, maybe check for nulls if we switch to binary reading later, but current `try-catch` on decode is a decent start).
