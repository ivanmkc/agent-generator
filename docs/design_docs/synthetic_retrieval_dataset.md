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

Validating relevance $R(q, d)$ for all $d \in D$ is intractable ($O(|Q| \times |D|)$). We approximate the global truth by validating a **High-Potential Subspace** $C(q)$.

#### Mathematical Formulation
Let $Rel(q)$ be the set of truly relevant documents for query $q$. We approximate $Rel(q)$ by evaluating only $d \in C(q)$, defined as:

$$ C(q) = C_{gold}(q) \cup C_{vector}(q, K_{vec}) \cup C_{random}(K_{rand}) $$

Where:
*   $C_{gold}(q)$: Documents identified by benchmark metadata (High Precision).
*   $C_{vector}(q, K_{vec})$: Top $K_{vec}$ results from a strong embedding model (High Recall).
*   $C_{random}(K_{rand})$: Randomly sampled documents (Statistical Control).

#### The Pooling Assumption
We assume that the probability of finding a relevant document outside our pool is negligible:
$$ P(d \in Rel(q) | d \notin C(q)) < \epsilon $$

**Validation of Assumption:** We monitor the impact of the **Random Control Group**.
*   If $\forall d \in C_{random}, \text{Impact}(d) \approx 0$, then the assumption holds (the "background" is noise).
*   If $\exists d \in C_{random}, \text{Impact}(d) \gg 0$, our retrieval mechanisms are insufficient (High "Background Radiation"), and we must increase $K_{vec}$ or improve the retrieval model.

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