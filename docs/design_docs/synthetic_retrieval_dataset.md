# Design Doc: Retrieval Dataset Generation (Benchmark Mining)

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-25

## 1. Problem Statement
Evaluating retrieval systems requires a ground-truth dataset where document relevance is proven via causal inference.

**Goal:** Automate the extraction of a high-quality retrieval dataset by mining benchmarks and using a **Monte Carlo Verification** process.

## 2. Methodology: Causal Relevance Verification

We determine document relevance by measuring its causal impact on task success: $P(\text{Success} | \text{Context Present}) - P(\text{Success} | \text{Context Absent})$.

### 2.1 Baseline: Zero-Context Success Rate
Before evaluating individual documents, we establish a baseline by running **N** trials with **no context at all**.
- **Metric:** $P(\text{Success} | \emptyset)$
- **Interpretation:** This measures the model's ability to solve the task from its **parametric memory alone**.
- **Utility:** A high zero-context success rate indicates the query is "easy" or "memorized," making it a poor candidate for evaluating retrieval effectiveness.

### 2.2 Sampling Strategies & Statistical Safety
The validator uses an **Adaptive Convergence** method, which stops trials when the **Adjusted Standard Error** ($SE \approx 1/N$) of the impact scores stabilizes below a threshold. This prevents premature stopping on lucky streaks.

### 2.3 The Scalability Trade-off: Stochastic Candidate Pooling
Verifying every document against every query is intractable. We validate a **High-Potential Subspace** ($C(q) = C_{gold} \cup C_{vector} \cup C_{random}$) and verify its completeness by checking if random documents have a non-zero impact score.

## 3. Failure Handling: Generation vs. Validation

To maintain data integrity, we distinguish between two failure modes:
1.  **Generation Failure:** The LLM fails to output a parsable, schema-compliant object. This is a transient error. The trial is **discarded** and a new one is attempted.
2.  **Validation Failure:** The LLM outputs a valid object with an incorrect answer. This is a valid data point and is recorded as a `FAIL` for statistical calculation.

## 4. Implementation Logic

The `DataValidator` runs the zero-context baseline, then proceeds with the Monte Carlo loop, retrying any generation failures.

## 5. Metrics & Evaluation Framework

### 5.1 Impact Score ($\Delta P$)
The primary scalar output for each document-query pair, representing the empirical lift in success probability.

### 5.2 Zero-Context Success Rate
Indicates task difficulty and model's prior knowledge. A dataset with a low average zero-context success rate is ideal for retrieval evaluation.