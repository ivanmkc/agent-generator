import yaml
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from rank_bm25 import BM25Okapi
from google import genai
import os
import asyncio
from tqdm.asyncio import tqdm

# --- Data Models ---
class RetrievalContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fqn: str
    text: str
    context_type: str = Field(..., alias="type")

class RetrievalPair(BaseModel):
    id: str
    query: str
    positive_ctxs: List[RetrievalContext]
    negative_ctxs: List[RetrievalContext]
    source: str
    metadata: Dict[str, Any]

class RetrievalDataset(BaseModel):
    pairs: List[RetrievalPair]

class RankedTarget(BaseModel):
    id: str # FQN
    name: str
    docstring: str = ""
    
    @property
    def corpus_text(self) -> str:
        return f"{self.name} {self.id} {self.docstring}"

# --- Retrievers ---
class AbstractRetriever(ABC):
    @abstractmethod
    async def index(self, documents: List[RankedTarget]):
        pass

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[RankedTarget]:
        pass

class BM25Retriever(AbstractRetriever):
    def __init__(self):
        self.bm25 = None
        self.documents = []

    async def index(self, documents: List[RankedTarget]):
        self.documents = documents
        tokenized_corpus = [doc.corpus_text.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_corpus)

    async def search(self, query: str, top_k: int = 5) -> List[RankedTarget]:
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_n = np.argsort(scores)[::-1][:top_k]
        return [self.documents[i] for i in top_n]

class EmbeddingRetriever(AbstractRetriever):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.documents = []
        self.embeddings = None

    async def _get_embeddings_batched(self, texts: List[str], batch_size: int = 100) -> np.ndarray:
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            # Parallelize calls within batch if supported, or just batch call
            # Gemini API supports batch embedding? Not easily via single call yet for diverse content
            # We'll do simple asyncio gather
            tasks = [
                self.client.aio.models.embed_content(
                    model="text-embedding-004",
                    contents=text,
                    config={"task_type": "RETRIEVAL_DOCUMENT"},
                )
                for text in batch
            ]
            batch_results = await asyncio.gather(*tasks)
            all_embeddings.extend([r.embeddings[0].values for r in batch_results])
        return np.array(all_embeddings)

    async def index(self, documents: List[RankedTarget]):
        self.documents = documents
        corpus_texts = [doc.corpus_text for doc in documents]
        # Cache check?
        cache_path = Path(".gemini/cache/vectors.npy")
        print(f"Indexing {len(documents)} documents. Cache path: {cache_path}")
        
        if cache_path.exists():
            cached = np.load(cache_path)
            print(f"Cache exists with shape: {cached.shape}")
            if len(cached) == len(documents):
                self.embeddings = cached
                print("Loaded embeddings from cache.")
                return

        print("Generating embeddings... this may take a moment.")
        self.embeddings = await self._get_embeddings_batched(corpus_texts)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache_path, self.embeddings)
        print(f"Saved embeddings to cache. Shape: {self.embeddings.shape}")

    async def search(self, query: str, top_k: int = 5) -> List[RankedTarget]:
        query_resp = await self.client.aio.models.embed_content(
            model="text-embedding-004",
            contents=query,
            config={"task_type": "RETRIEVAL_QUERY"},
        )
        query_vec = np.array(query_resp.embeddings[0].values)
        
        # Cosine Similarity
        scores = np.dot(self.embeddings, query_vec)
        top_n = np.argsort(scores)[::-1][:top_k]
        return [self.documents[i] for i in top_n]

# --- Evaluation ---
class RetrievalEvaluator:
    def __init__(self, dataset_path: str, targets_path: str):
        with open(dataset_path, 'r') as f:
            self.dataset = RetrievalDataset.model_validate(yaml.safe_load(f))
        
        with open(targets_path, 'r') as f:
            data = yaml.safe_load(f)
            raw_targets = data if isinstance(data, list) else data.get('targets', [])
            self.targets = [RankedTarget(id=t['id'], name=t['name'], docstring=t.get('docstring', '')) for t in raw_targets if t.get('id')]

    async def run_benchmark(self, retriever: AbstractRetriever, name: str) -> Dict[str, float]:
        await retriever.index(self.targets)
        
        recall_at_1 = 0
        recall_at_5 = 0
        mrr = 0
        
        print(f"Benchmarking {name}...")
        for pair in tqdm(self.dataset.pairs):
            gold_fqns = {ctx.fqn for ctx in pair.positive_ctxs}
            results = await retriever.search(pair.query, top_k=5)
            result_fqns = [r.id for r in results]
            
            # Recall@1
            if result_fqns[0] in gold_fqns:
                recall_at_1 += 1
                
            # Recall@5
            if any(fqn in gold_fqns for fqn in result_fqns):
                recall_at_5 += 1
                
            # MRR
            for i, fqn in enumerate(result_fqns):
                if fqn in gold_fqns:
                    mrr += 1.0 / (i + 1)
                    break
        
        total = len(self.dataset.pairs)
        return {
            "model": name,
            "recall@1": recall_at_1 / total,
            "recall@5": recall_at_5 / total,
            "mrr": mrr / total
        }
