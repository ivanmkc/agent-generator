"""
CLI tool to execute the RAG retrieval evaluation suite.

This script runs the defined retrievers (BM25, Embedding, etc.) against the
`retrieval_dataset` and computes quantitative metrics (Recall, MRR).
Results are saved to `retrieval_evals/`.
"""

import asyncio
import os
import sys
import pandas as pd
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from tools.retrieval_benchmark_lib import RetrievalEvaluator, BM25Retriever, EmbeddingRetriever


async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set.")
        return

    evaluator = RetrievalEvaluator(
        dataset_path="retrieval_dataset.yaml",
        targets_path="benchmarks.generator.benchmark_generator/data/ranked_targets.yaml",
    )

    print(
        f"Loaded {len(evaluator.dataset.pairs)} queries and {len(evaluator.targets)} targets."
    )

    # 1. BM25
    bm25 = BM25Retriever()
    res_bm25 = await evaluator.run_benchmark(bm25, "BM25")

    # 2. Embeddings
    emb = EmbeddingRetriever(api_key=api_key)
    res_emb = await evaluator.run_benchmark(emb, "Gemini Embeddings")

    # Results
    df = pd.DataFrame([res_bm25, res_emb])
    print("\nResults:")
    print(df)


if __name__ == "__main__":
    asyncio.run(main())
