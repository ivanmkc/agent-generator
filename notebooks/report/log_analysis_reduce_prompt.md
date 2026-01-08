You are a Lead AI Engineer creating a final Benchmark Execution Report.
Below are individual analyses of different components/generators from the run.
Synthesize these into a cohesive, high-level report.

**Report Structure:**

# 📊 Benchmark Run Analysis

## 1. Generator Internals & Configuration
*   **Instruction:** Using the **Generator Context** provided below, describe the architecture of the generators used in *this specific run*.
*   **Detail:** Replace any placeholders with the actual model names found in the context.

## 2. Executive Summary
*   High-level overview of the session.
*   **Use the 'Quantitative Stats' provided below** to cite precise Pass Rates (e.g., "82.5% passed"). Do NOT guess stats from the logs.

## 3. Generator Analysis
*   Provide a dedicated sub-section for each generator.
*   **Stats:** Start with a summary line: "Pass Rate: X% (N/M passed) | Avg Latency: Ys". Use the Quantitative Stats.
*   **Performance:** Discuss stability and any per-suite patterns found in the logs.

## 4. Cross-Generator Comparison
*   Compare generators on Quality, Latency, and Stability.
*   Use the Quantitative Stats to back up your claims (e.g., "Generator A was 2x faster than B").

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
*   Actionable steps to fix errors or improve performance.

---
**Quantitative Stats (Ground Truth):**
{quantitative_context}

**Generator Context (Scaffold):**
{static_context}
---

--- COMPONENT ANALYSES START ---
{combined_text}
--- COMPONENT ANALYSES END ---

Output the final report in Markdown.