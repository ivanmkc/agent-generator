This system creates a "Golden Dataset" for training search tools by figuring out which documents *actually* help an AI answer a question. It does this by running experiments: it asks the AI a question with and without a specific document and measures if the answer gets better. This filters out questions the AI already knows the answer to and finds documents that truly make a difference. This helps us build better search engines for AI.

**High-Level Subtasks:**
- **Baseline Check:** Ask the AI questions *without* any help to see what it already knows. If it answers correctly on its own, we don't need a search tool for that question.
- **Gather Candidates:** Pick a few documents that *might* be useful (e.g., using keywords or vector search).
- **Verify Helpfulness:** Run a series of tests: "Does adding Document X help the AI answer Question Y correctly more often?" We repeat this until we are sure the improvement isn't just luck.
- **Create Dataset:** Save the winning pairs (Question + Helpful Document) into a file. We can use this file to train smarter search tools.

**Pseudocode:**
```python
for question in questions:
    # 1. Baseline: Can the AI answer this alone?
    score_alone = test_ai(question, context=None)
    if score_alone > 0.8:
        continue # Skip easy questions

    # 2. Gather Candidates: Find potentially useful docs
    candidates = search_docs(question)

    for doc in candidates:
        # 3. Verify Helpfulness: Does this specific doc help?
        score_with_doc = test_ai(question, context=doc)
        
        improvement = score_with_doc - score_alone
        
        if improvement > 0.1: # If it helps significantly
            save_to_dataset(question, doc, improvement)
```