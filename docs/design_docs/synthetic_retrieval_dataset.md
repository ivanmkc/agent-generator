# Design Doc: Retrieval Dataset Generation (Benchmark Mining)

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Evaluating and optimizing the retrieval component of an RAG system requires a ground-truth dataset where the relevance of a document to a query is **empirically proven** via statistical causal inference.

**Goal:** Automate the extraction of a high-quality retrieval dataset by mining benchmarks and using a **Monte Carlo Verification** process to establish the causal impact of specific documents on task success.

## 2. Methodology: Monte Carlo Relevance Verification

We treat all potential documents as **candidates**. Their status is determined by whether their presence increases the probability of solving the task ($P(Success | Ctx) - P(Success | \neg Ctx)$).

### 2.1 Sampling Strategies

The validator supports two execution modes to balance precision and cost:

1.  **Constant Trial Method (Default):**
    *   Runs a fixed number of trials ($N$) for every case.
    *   Ensures uniform statistical power across the entire dataset.
    *   Recommended for small, high-stakes evaluations.

2.  **Adaptive Convergence Method (Optional):**
    *   Intelligently determines the number of trials based on statistical stability.
    *   **Stopping Rule:** Trials terminate early if the **Standard Error (SE)** of the impact scores falls below a target threshold (e.g., 0.05).
    *   **Benefit:** Saves significant API quota on "easy" queries where relevance is obvious after a few trials, while investing more heavily in "noisy" or difficult queries.

### 2.2 Statistical Principles
*   **Causal Inference:** The method functions as a Randomized Controlled Trial (RCT).
*   **Power Analysis:** Standard Error calculation ($\sqrt{p(1-p)/n}$) provides a measure of estimate confidence.
*   **Blind Solving:** The model has no metadata regarding which documents are "seeded" vs. "sampled," ensuring an unbiased measure of document utility.

## 3. Implementation Logic

The `DataValidator` encapsulates the sampling logic, supporting both modes via parameterization:

```python
validator.validate_case(case, mode="fixed", n_trials=10)
# OR
validator.validate_case(case, mode="adaptive", se_threshold=0.05, max_trials=30)
```

## 4. Metrics & Evaluation Framework

### 4.1 Recall at K (Recall@K)
The proportion of queries where at least one document with a high **Positive Impact Score** appears in the top `K`.

### 4.2 Set Recall (Kernel Completeness)
For complex tasks requiring multiple documents, this measures the fraction of the "Winning Coalition" (documents that together yield Success=1) found in the results.

### 4.3 Impact Score (Delta P)
The primary scalar output for each document-query pair, representing the empirical lift in success probability.
