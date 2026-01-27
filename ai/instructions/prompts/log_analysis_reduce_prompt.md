You are a Lead AI Engineer creating a final Benchmark Execution Report.
Below are individual analyses of different components/generators from the run.
Synthesize these into a cohesive, high-level report that respects the hierarchy of Generators -> Suites -> Cases -> Attempts.

**Report Structure:**

# 📊 Benchmark Run Analysis

## 1. Generator Internals & Configuration
*   **Instruction:** Describe the architecture of the generators used in *this specific run* using the **Generator Context** provided below.
*   **CRITICAL REQUIREMENT:** You MUST preserve the high-fidelity technical details from the context for each generator. 
*   **For each generator, you must include:**
    1.  The **Environment** description.
    2.  The full list of **Tools** (clearly distinguishing between **Built-in** and **Custom MCP** tools).
    3.  The **Strategy** description (e.g., "Code -> Run -> Fix" vs "Research -> Code -> Run -> Fix").
*   **Note:** Do NOT summarize these details into a single sentence. The performance differences in the report are explained by these specific toolsets, so they must be visible to the reader.

## 2. Executive Summary
*   High-level overview of the session, organized by Generator and Suite.
*   **Use the 'Quantitative Stats' provided below** to cite precise **Case Pass Rates** and **Attempt Success Rates**. Do NOT guess stats from the logs.

## 3. Benchmark Suites Overview
*   Briefly describe the benchmark suites executed in this run (e.g., `api_understanding`, `fix_errors`).
*   Explain the objective of each suite (e.g., "Tests the model's ability to recall correct import paths and class signatures without hallucination").

## 4. Quantitative Analysis (Ground Truth)
*   **Instruction:** Directly include the **Quantitative Stats** tables provided below in this section. Do NOT summarize them into oblivion; the raw tables are essential for the report.
*   Ensure the following are present:
    *   Results by Generator & Suite
    *   Token Usage & Cost Summary
    *   Tool Success Rates

## 4. Generator Analysis
*   Provide a dedicated sub-section for each generator.
*   **Stats:** Start with a summary line: "Case Pass Rate: X% | Attempt Success Rate: Y% | Avg Latency: Zs". Use the Quantitative Stats.
*   **Performance:** Discuss stability, retry patterns, and any per-suite patterns found in the logs.

## 5. Cross-Generator Comparison
*   Compare generators on Quality, Efficiency (Attempts per Case), Latency, and Stability.
*   Use the Quantitative Stats to back up your claims (e.g., "Generator A required 1.2 attempts/case vs Generator B's 2.5").

## 6. Root Cause Analysis
### 6.0 Global Summary
*   Summarize the most common themes across all generators.

### 6.[N] [Generator Name]
A detailed breakdown of failures for this generator, maintaining hierarchy awareness (mentioning specific Suites/Cases):
#### Docs/Context Injection
*   Analyze the quality and relevance of documentation/context provided to the model.
*   Identify if failures were due to "context blindness" or lack of information.
#### Tool Usage
*   Analyze the effectiveness of tool calls across attempts.
*   Note any recurring tool errors or inefficient search patterns.
#### General Errors
*   Logic errors, syntax errors, or timeouts.

## 7. Recommendations
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