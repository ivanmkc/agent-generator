# Benchmark Metrics Report - 2026-02-03

## Run Summary

- **Run ID:** 2026-02-03_22-53-17
- **Generators:** `ranked_knowledge_remote_main` vs `ranked_knowledge_vector`
- **Model:** gemini-2.5-flash
- **Suites:** All 5 standard suites.

## Pass Rates by Suite

| Generator | Suite | Pass Rate | Pass/Total |
| :--- | :--- | :--- | :--- |
| **ranked_knowledge_remote_main** | api_understanding | 90.2% | 37/41 |
| | configure_adk_features_mc | 90.2% | 74/82 |
| | diagnose_setup_errors_mc | 81.2% | 26/32 |
| | **fix_errors** | **87.0%** | **20/23** |
| | predict_runtime_behavior_mc | 70.6% | 12/17 |
| **ranked_knowledge_vector** | api_understanding | 97.6% | 40/41 |
| | configure_adk_features_mc | 91.5% | 75/82 |
| | diagnose_setup_errors_mc | 84.4% | 27/32 |
| | fix_errors | 73.9% | 17/23 |
| | predict_runtime_behavior_mc | 82.4% | 14/17 |

## Analysis

- **`api_understanding`**: The local `vector` setup had a near-perfect score (97.6%) compared to the `remote_main` (90.2%). This suggests the local pre-computed index might be slightly more precise or comprehensive for browsing symbols.
- **`fix_errors`**: **`remote_main` outperformed `vector` significantly (87.0% vs 73.9%)**. This implies that for coding tasks, the dynamic cloning and reading of source files might provide more relevant or readable context than the local index retrieval in some cases.
- **`predict_runtime_behavior_mc`**: The `vector` setup was stronger here (82.4% vs 70.6%). This suite requires deep understanding of subtle interactions, which the local index might capture more consistently.
- **MC Suites**: Performance was comparable across `configure_adk_features` and `diagnose_setup_errors`, confirming that both setups are effective for general framework knowledge.
