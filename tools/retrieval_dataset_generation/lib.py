import yaml
import numpy as np
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Literal, Optional
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from rank_bm25 import BM25Okapi
from google import genai
import os
import asyncio
from tqdm.asyncio import tqdm

# --- Configuration ---
class ValidatorConfig(BaseModel):
    """Configuration for the Retrieval Data Validator."""
    monte_carlo_trials: int = Field(3, description="Number of trials for fixed sampling.")
    gold_miner_k: int = Field(100, description="Max candidates to mine from Ground Truth.")
    vector_search_k: int = Field(15, description="Number of candidates to retrieve via Vector Search.")
    random_noise_n: int = Field(20, description="Number of random noise documents to add.")
    adaptive_min_n: int = Field(5, description="Minimum trials for adaptive mode.")
    adaptive_max_n: int = Field(40, description="Maximum trials for adaptive mode.")
    se_threshold: float = Field(0.1, description="Standard Error threshold for convergence.")

# --- Data Models ---

class RetrievalResultMetadata(BaseModel):
    """
    Metadata capturing the empirical performance of a retrieval candidate.
    """
    delta_p: float = Field(
        0.0, 
        description="Impact Score: The change in success probability when this document is present vs absent. "
                    "Range: [-1.0, 1.0]. Positive values indicate the document helps; negative values indicate it harms."
    )
    p_in: float = Field(
        0.0,
        description="Probability of Success given IN: Success rate of trials where this document was included in the context."
    )
    p_out: float = Field(
        0.0,
        description="Probability of Success given OUT: Success rate of trials where this document was excluded from the context."
    )
    n_in: int = Field(0, description="Number of trials where this document was included.")
    n_out: int = Field(0, description="Number of trials where this document was excluded.")
    se_in: float = Field(0.0, description="Standard Error of p_in.")
    se_out: float = Field(0.0, description="Standard Error of p_out.")
    
    # Allow extra fields
    model_config = ConfigDict(extra='allow')

class RetrievalContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fqn: str
    text: str
    context_type: str = Field(..., alias="type")
    empirical_relevance: str = "UNKNOWN"
    metadata: RetrievalResultMetadata = Field(default_factory=RetrievalResultMetadata)

class RetrievalCase(BaseModel):
    id: str
    query: str
    positive_ctxs: List[RetrievalContext] = Field(default_factory=list)
    negative_ctxs: List[RetrievalContext] = Field(default_factory=list)
    source: str
    metadata: Dict[str, Any]
    ground_truth: Dict[str, Any] = Field(default_factory=dict)
    is_sufficient_set: bool = False
    candidates: List[RetrievalContext] = Field(default_factory=list) # Unified pool

class RetrievalDataset(BaseModel):
    cases: List[RetrievalCase]

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
    async def search(self, query: str, top_k: int = 5, case: Optional[RetrievalCase] = None) -> List[RankedTarget]:
        pass

class BM25Retriever(AbstractRetriever):
    def __init__(self):
        self.bm25 = None
        self.documents = []

    async def index(self, documents: List[RankedTarget]):
        self.documents = documents
        tokenized_corpus = [doc.corpus_text.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_corpus)

    async def search(self, query: str, top_k: int = 5, case: Optional[RetrievalCase] = None) -> List[RankedTarget]:
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
        cache_path = Path(".gemini/cache/vectors.npy")
        print(f"Indexing {len(documents)} documents. Cache path: {cache_path}")
        
        if cache_path.exists():
            cached = np.load(cache_path)
            if len(cached) == len(documents):
                self.embeddings = cached
                print("Loaded embeddings from cache.")
                return

        print("Generating embeddings... this may take a moment.")
        self.embeddings = await self._get_embeddings_batched(corpus_texts)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache_path, self.embeddings)

    async def search(self, query: str, top_k: int = 5, case: Optional[RetrievalCase] = None) -> List[RankedTarget]:
        if self.embeddings is None:
            raise ValueError("Retriever index not loaded.")
            
        # Use CODE_RETRIEVAL_QUERY for code/ADK symbol search
        # Note: Previous run failed with 400 because text-embedding-004 might not support CODE_RETRIEVAL_QUERY yet
        # or the client lib mapping is specific. Reverting to RETRIEVAL_QUERY for safety as per turn 112 fix.
        query_resp = await self.client.aio.models.embed_content(
            model="text-embedding-004",
            contents=query,
            config={"task_type": "RETRIEVAL_QUERY"},
        )
        query_vec = np.array(query_resp.embeddings[0].values)
        scores = np.dot(self.embeddings, query_vec)
        top_n = np.argsort(scores)[::-1][:top_k]
        return [self.documents[i] for i in top_n]

class RandomRetriever(AbstractRetriever):
    def __init__(self):
        self.documents = []

    async def index(self, documents: List[RankedTarget]):
        self.documents = documents

    async def search(self, query: str, top_k: int = 5, case: Optional[RetrievalCase] = None) -> List[RankedTarget]:
        return random.sample(self.documents, min(top_k, len(self.documents)))

class GoldMinerRetriever(AbstractRetriever):
    """Retrieves candidates based on 'Gold' metadata in the case."""
    def __init__(self):
        self.documents = []
        self.fqn_map = {}

    async def index(self, documents: List[RankedTarget]):
        self.documents = documents
        self.fqn_map = {doc.id: doc for doc in documents}

    async def search(self, query: str, top_k: int = 5, case: Optional[RetrievalCase] = None) -> List[RankedTarget]:
        if not case:
            return []
        
        results = []
        for ctx in case.positive_ctxs:
            if ctx.fqn in self.fqn_map:
                results.append(self.fqn_map[ctx.fqn])
        
        return results

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
        for case in tqdm(self.dataset.cases):
            gold_fqns = {ctx.fqn for ctx in case.positive_ctxs}
            results = await retriever.search(case.query, top_k=5, case=case)
            result_fqns = [r.id for r in results]
            
            if result_fqns and result_fqns[0] in gold_fqns:
                recall_at_1 += 1
            if any(fqn in gold_fqns for fqn in result_fqns):
                recall_at_5 += 1
            for i, fqn in enumerate(result_fqns):
                if fqn in gold_fqns:
                    mrr += 1.0 / (i + 1)
                    break
        
        total = len(self.dataset.cases)
        return {
            "model": name,
            "recall@1": recall_at_1 / total,
            "recall@5": recall_at_5 / total,
            "mrr": mrr / total
        }