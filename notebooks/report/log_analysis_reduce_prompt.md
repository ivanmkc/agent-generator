You are a Lead AI Engineer creating a final Benchmark Execution Report.
Below are individual analyses of different components/generators from the run.
Synthesize these into a cohesive, high-level report.

**Report Structure:**

# 📊 Benchmark Run Analysis

## 1. Generator Internals & Configuration
*   **Context:** Use the 'Configuration Context' provided below to describe the technical architecture (Single Agent vs Multi-Agent, Index vs Tool-based retrieval).

## 2. Executive Summary
*   High-level overview of the session (success/failure, major issues).

## 3. Generator Analysis
*   Summary table of results (Pass Rate, Latency).

## 4. Cross-Generator Comparison
*   Compare generators on Quality, Latency, and Stability.

## 5. Root Cause Analysis
### 5.0 Global Summary
*   Summarize the most common themes across all generators.

### 5.[N] [Generator Name]
A detailed breakdown of failures for this generator:
#### Docs/Context Injection
*   Analyze the quality and relevance of documentation/context provided to the model.
*   Identify if failures were due to "context blindness" or lack of information.
#### Tool Usage
*   Analyze the effectiveness of tool calls.
*   Note any recurring tool errors or inefficient search patterns.
#### General Errors
*   Logic errors, syntax errors, or timeouts.

## 6. Recommendations
*   Actionable steps to fix identified issues.

---
**Configuration Context:**
{static_context}
---

--- COMPONENT ANALYSES START ---
{combined_text}
--- COMPONENT ANALYSES END ---

Output the final report in Markdown.