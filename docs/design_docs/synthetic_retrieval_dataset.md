# Design Doc: Retrieval Dataset Generation (Benchmark Mining)

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Evaluating and optimizing the retrieval component of an RAG system requires a ground-truth dataset where the relevance of a document to a query is **empirically proven** via statistical causal inference.

**Goal:** Automate the extraction of a high-quality retrieval dataset by mining benchmarks and using a **Monte Carlo Verification** process to establish the causal impact of specific documents on task success.

## 2. Methodology: Monte Carlo Relevance Verification

We treat all potential documents as **candidates**. Their status is determined by whether their presence increases the probability of solving the task ($P(Success | Ctx) - P(Success | \neg Ctx)$).

### 2.1 Sampling Strategies (Validation Convergence)
The validator supports two execution modes to balance precision and cost:
1.  **Constant Trial Method:** Runs fixed $N$ trials per case.
2.  **Adaptive Convergence Method:** Stops early if the Standard Error of impact scores stabilizes.

### 2.2 Dataset-Level Convergence (Global)
We monitor the stability of aggregate metrics (e.g., Mean Recall@5) as we add more *cases* to the dataset to ensure the corpus is sufficiently covered.

### 2.3 The Scalability Trade-off: Stochastic Candidate Pooling
Verifying relevance for *every* document against *every* query is computationally intractable ($O(\text{Queries} \times \text{Corpus})$).

**The Middle Ground:** We validate a **High-Potential Subspace** ($O(\text{Queries} \times K)$) constructed from three sources:
1.  **Vector Search ($K_{retrieved} \approx 15$):** Uses a strong embedding model to capture the vast majority of potentially relevant documents. This acts as a "High Recall" filter.
2.  **Gold Mining ($K_{gold} \approx 1-5$):** Uses benchmark metadata to inject "High Precision" candidates that search might miss.
3.  **Random Control ($K_{random} \approx 5$):** A statistical control group.
    *   *Hypothesis:* If $Impact(Random) \approx 0$, we can statistically assume the un-sampled tail of the corpus is also irrelevant.
    *   *Check:* If random docs frequently show high impact, our candidate generation (Vector Search) is failing, and we must increase $K_{random}$.

### 2.4 Statistical Principles
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
