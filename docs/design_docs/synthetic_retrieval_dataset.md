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
Verifying relevance $R(q, d)$ for all $d \in D$ is intractable ($O(|Q| \times |D|)$). We approximate the global truth by validating a **High-Potential Subspace** $C(q)$ derived from Gold Mining, Vector Search ($K_{vec}$), and Random Control ($K_{rand}$). 

### 2.4 Statistical Principles: Confidence at Boundaries & Safety Analysis

A naive Standard Error calculation ($SE = \sqrt{p(1-p)/n}$) is flawed for small sample sizes, particularly at the boundaries ($p=0$ or $p=1$), where it yields $SE=0$. This creates a **"Premature Stopping Risk"**: 2 consecutive successes ($n=2, p=1$) would calculate $SE=0$ and trigger a stop, despite having virtually no statistical significance.

**Solution: Adjusted Confidence Metric**
We use an **Adjusted Standard Error** that imposes a minimum uncertainty floor based on sample size:

$$ SE_{adjusted} = \begin{cases} \sqrt{\frac{p(1-p)}{n}} & \text{if } 0 < p < 1 \ \frac{1}{n} & \text{if } p=0 \text{ or } p=1 \end{cases} $$

**Safety Proof:**
To satisfy a convergence threshold of $\epsilon = 0.1$:
*   **Best Case (Uniform Results):** If a document works 100% of the time ($p=1$), we use $SE = 1/n$. To reach $1/n < 0.1$, we require **$n > 10$ trials**.
*   **Worst Case (High Variance):** If a document works 50% of the time ($p=0.5$), $SE = \sqrt{0.25/n} = 0.5/\sqrt{n}$. To reach $0.5/\sqrt{n} < 0.1$, we require $\sqrt{n} > 5 \Rightarrow$ **$n > 25$ trials**.

This guarantees that the system **cannot** stop early on a "lucky streak" of 3-4 trials. It forces substantial evidence gathering before declaring convergence.

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