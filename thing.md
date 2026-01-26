This system builds a high-quality dataset for training retrievers by rigorously verifying which documents actually help an AI solve a specific task. Instead of assuming relevance based on keywords, it runs controlled experiments: does the AI's success rate improve when this document is present? This filters out irrelevant noise and easy questions that don't need retrieval, creating a ground-truth standard for "helpful context".

**High-Level Subtasks:**
- **Baseline Check:** Verify if the task actually requires external information. If the AI can solve it using only its internal knowledge, it's not a good test for retrieval.
- **Candidate Pooling:** Gather a broad set of potentially useful documents using various search methods (like vector search or keyword matching) and some random ones for noise.
- **Experimental Verification:** Run many randomized trials. In each trial, give the AI a random subset of the documents and see if it succeeds.
- **Impact Analysis:** Analyze the results to calculate an "Impact Score" for each document. A high score means the AI succeeds much more often when that specific document is included.
- **Dataset Creation:** Compile the questions and their proven-to-be-helpful documents into a verified dataset.

**Pseudocode:**
```python
for case in benchmark_cases:
    # 1. Baseline: Can the AI solve this without help?
    baseline_score = run_trials(case, context=[])
    if baseline_score > threshold: continue # Too easy, skip

    # 2. Pool Candidates: Find potentially useful docs
    candidates = retrieve_candidates(case.query)

    # 3. Monte Carlo Verification: Randomized trials
    for trial in range(N_TRIALS):
        # Randomly select a subset of candidates to include
        subset = random_sample(candidates)
        success = run_trial(case, context=subset)
        record_result(subset, success)

    # 4. Calculate Impact: Did a specific doc cause success?
    for doc in candidates:
        # Compare success rate when doc was present vs absent
        score_with = success_rate(where doc in subset)
        score_without = success_rate(where doc not in subset)
        impact = score_with - score_without

        if impact > significant_threshold:
            mark_as_relevant(case, doc)
```