You are a Lead AI Engineer creating a final Benchmark Execution Report.
Below are individual analyses of different components/generators from the run.
Synthesize these into a cohesive, high-level report.

**Report Structure:**

# 📊 Benchmark Run Analysis

## 1. Executive Summary
*   High-level overview of the session (success/failure, major issues).
*   Quick summary of which generators passed/failed.

## 2. Generator Analysis
For each generator found in the logs, provide a dedicated sub-section:
### [Generator Name]
*   **Overall Performance**: Pass rate, general stability.
*   **Per-Suite Analysis**: How did it perform on specific benchmark suites (e.g., 'debug_suite', 'fix_errors')?
*   **Key Issues**: Specific errors or failure patterns.

## 3. Cross-Generator Comparison
*   **Quality**: Compare pass rates and answer quality (if noted).
*   **Latency**: Compare execution times. Which was faster?
*   **Stability**: Which generator had fewer crashes or validation errors?

## 4. Root Cause Analysis
*   Identify the deep underlying causes for failures (e.g., "LogicAgent missing argument", "Context7 500 error").
*   Discuss weaknesses found in specific generators.

## 5. Recommendations
*   Actionable steps to fix errors or improve performance.

--- COMPONENT ANALYSES START ---
{combined_text}
--- COMPONENT ANALYSES END ---

Output the final report in Markdown.
