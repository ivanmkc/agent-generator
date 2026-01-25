#!/usr/bin/env python3
import yaml
import logging
import asyncio
import os
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from google import genai
from tqdm.asyncio import tqdm

# Reuse models or redefine
class RetrievalContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fqn: str
    text: str
    context_type: str = Field(..., alias="type")
    empirical_relevance: str = "UNKNOWN" # YES, NO

class RetrievalPair(BaseModel):
    id: str
    query: str
    positive_ctxs: List[RetrievalContext]
    negative_ctxs: List[RetrievalContext]
    source: str
    metadata: Dict[str, Any]

class RetrievalDataset(BaseModel):
    pairs: List[RetrievalPair]

class DataValidator:
    def __init__(self, input_path: str, output_path: str, api_key: str):
        self.input_path = input_path
        self.output_path = output_path
        self.client = genai.Client(api_key=api_key)
        
    async def validate_dataset(self):
        with open(self.input_path, 'r') as f:
            dataset = RetrievalDataset.model_validate(yaml.safe_load(f))
        
        print(f"Validating {len(dataset.pairs)} pairs...")
        
        # Limit for dev
        # dataset.pairs = dataset.pairs[:5]
        
        tasks = []
        for pair in dataset.pairs:
            tasks.append(self.validate_pair(pair))
        
        # Run in chunks to avoid rate limits
        chunk_size = 5
        results = []
        for i in tqdm(range(0, len(tasks), chunk_size)):
            chunk = tasks[i:i+chunk_size]
            results.extend(await asyncio.gather(*chunk))
            
        dataset.pairs = results
        
        # Save
        print(f"Saving verified dataset to {self.output_path}...")
        with open(self.output_path, 'w') as f:
            yaml.dump(dataset.model_dump(by_alias=True), f, sort_keys=False, allow_unicode=True)

    async def validate_pair(self, pair: RetrievalPair) -> RetrievalPair:
        # Validate Positives
        new_pos = []
        new_neg = []
        
        # Check existing positives
        for ctx in pair.positive_ctxs:
            is_relevant = await self._check_relevance(pair.query, ctx.text)
            ctx.empirical_relevance = "YES" if is_relevant else "NO"
            if is_relevant:
                new_pos.append(ctx)
            else:
                # Demote to negative
                ctx.context_type = "negative"
                new_neg.append(ctx)
                
        # Check existing negatives (optional, to find hard positives?)
        # For now, just keep them as negative but label them NO
        for ctx in pair.negative_ctxs:
             # We can verify them too to be sure
             is_relevant = await self._check_relevance(pair.query, ctx.text)
             ctx.empirical_relevance = "YES" if is_relevant else "NO"
             if is_relevant:
                 # Promote to positive!
                 ctx.context_type = "gold_mined"
                 new_pos.append(ctx)
             else:
                 new_neg.append(ctx)
        
        pair.positive_ctxs = new_pos
        pair.negative_ctxs = new_neg
        return pair

    async def _check_relevance(self, query: str, context: str) -> bool:
        prompt = f"""User Question: {query}

Context:
{context[:2000]} ... (truncated)

Task: Can you answer the user's question definitively using ONLY the provided context?
If the context contains the specific class, method, or explanation required to answer, say YES.
If the context is irrelevant, unrelated, or missing key details, say NO.

Answer (YES/NO):"""

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-3-pro-preview",
                contents=prompt
            )
            ans = response.text.strip().upper()
            return "YES" in ans
        except Exception as e:
            print(f"Error checking relevance: {e}")
            return False # Default to conservative

if __name__ == "__main__":
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set")
        exit(1)
        
    validator = DataValidator(
        "retrieval_dataset.yaml",
        "retrieval_dataset_verified.yaml",
        api_key
    )
    asyncio.run(validator.validate_dataset())
