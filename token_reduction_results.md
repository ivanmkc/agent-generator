# Token Reduction Results

## Experiment 1: History Toggle (2026-01-06)
*Result:* Disabling history **increased** tokens due to analyst tool explosion.

## Experiment 2: Tool Limits & Smart Logs (2026-01-06)
*Result:* **Smart Logs** controlled Analyst tokens (28k vs 546k). However, **Planner** exploded (124k) by using tools excessively.

## Experiment 3: Toolless Planners + Strict Limits (2026-01-06)

**Configuration:**
- **Toolless Planners:** `implementation_planner` and `verification_planner` stripped of exploration tools.
- **Strict File Limits:** `read_file` limited to 500 lines / 1000 chars.
- **Smart Logs:** Active.

**Results on Case 22:**
| Metric | SmartLogs Only (Run 3) | **Toolless + Strict (Run 4)** |
| :--- | :--- | :--- |
| **Total Tokens** | ~411k (3 attempts) | **~196k (1 attempt)** |
| **Impl. Planner** | 124k | **18k** (85% reduction) |
| **Candidate Creator** | 250k | **139k** (44% reduction) |
| **Run Analyst** | 28k | **31k** (Consistent) |

**Conclusion:**
- **Planner Optimization:** Removing tools from the planner was the most impactful change, reducing its own usage by 85% and significantly reducing the downstream context for the Candidate Creator.
- **System Efficiency:** The system is now lean and focused. The planner relies on retrieval, the candidate relies on the plan, and the analyst relies on summaries.

**Recommendation:**
Deploy these changes to production. The combination of **Smart Logs**, **Toolless Planners**, and **Output Limits** provides the best balance of capability and token efficiency.
