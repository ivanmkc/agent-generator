#!/usr/bin/env python3
import yaml
import logging
import asyncio
import os
import sys
import random
from typing import List, Dict, Any, Literal, Optional
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from google import genai
from tqdm.asyncio import tqdm

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from benchmarks.data_models import (
    ApiUnderstandingBenchmarkCase, FixErrorBenchmarkCase, 
    ApiUnderstandingAnswerOutput, FixErrorAnswerOutput, 
    BenchmarkType, AnswerTemplate, StringMatchAnswer, GeneratedAnswer,
    BenchmarkResultType, CodeSnippetRef
)
from benchmarks.benchmark_runner import ApiUnderstandingRunner, PytestBenchmarkRunner
from benchmarks.config import MOST_POWERFUL_MODEL
from benchmarks.parsing.json_sanitizer import JsonSanitizer
from benchmarks.api_key_manager import API_KEY_MANAGER

# Reuse models or redefine
class RetrievalContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fqn: str
    text: str
    context_type: str = Field(..., alias="type")
    empirical_relevance: str = "UNKNOWN" # YES, NO
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RetrievalPair(BaseModel):
    id: str
    query: str
    positive_ctxs: List[RetrievalContext]
    negative_ctxs: List[RetrievalContext]
    source: str
    metadata: Dict[str, Any]
    ground_truth: Dict[str, Any] = Field(default_factory=dict)
    is_sufficient_set: bool = False

class RetrievalDataset(BaseModel):
    pairs: List[RetrievalPair]

class DataValidator:
    def __init__(self, input_path: str, output_path: str, api_key: str):
        self.input_path = input_path
        self.output_path = output_path
        self.client = genai.Client(api_key=api_key)
        self.sanitizer = JsonSanitizer(api_key_manager=API_KEY_MANAGER)
        
    async def validate_dataset(self):
        with open(self.input_path, 'r') as f:
            dataset = RetrievalDataset.model_validate(yaml.safe_load(f))
        
        print(f"Validating {len(dataset.pairs)} pairs...")
        
        # Limit for dev
        # dataset.pairs = dataset.pairs[:5] # Use small subset for Monte Carlo test
        
        tasks = []
        for pair in dataset.pairs:
            tasks.append(self.validate_pair(pair))
        
        # Run in chunks
        chunk_size = 2 # Small chunk size for heavy MC tasks
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
        """
        Validates the pair by establishing statistical conditional dependence of success on each context.
        """
        # 1. Pool Candidates
        candidates = pair.positive_ctxs + pair.negative_ctxs
        if not candidates:
            return pair

        # Map by FQN
        c_map = {c.fqn: c for c in candidates}
        fqns = list(c_map.keys())
        
        # Stats
        trials_in = {f: 0 for f in fqns}
        success_in = {f: 0 for f in fqns}
        trials_out = {f: 0 for f in fqns}
        success_out = {f: 0 for f in fqns}
        
        N_TRIALS = 3  # Keep small for dev
        
        print(f"  - Running {N_TRIALS} Monte Carlo trials for pair {pair.id}...")
        
        for i in range(N_TRIALS):
            # 2. Monte Carlo Subsampling (Bernoulli p=0.5)
            subset_fqns = []
            while not subset_fqns:
                subset_fqns = [f for f in fqns if random.random() > 0.5]
                if not subset_fqns and fqns:
                    subset_fqns = [random.choice(fqns)]
            
            subset_ctxs = [c_map[f] for f in subset_fqns]
            
            # 3. Generate & Validate
            combined_text = "\n\n".join([f"Document {i}: {c.text}" for i, c in enumerate(subset_ctxs)])
            
            is_success = False
            generated_answer = await self._generate_answer(pair, combined_text)
            if generated_answer:
                try:
                    if pair.source == "api_understanding":
                        is_success = await self._validate_api_understanding(pair, generated_answer)
                    elif pair.source == "fix_errors":
                        is_success = await self._validate_fix_errors(pair, generated_answer)
                except Exception as e:
                    print(f"Validation exception for {pair.id}: {e}")
                    is_success = False
            
            # 4. Record Stats
            for f in fqns:
                if f in subset_fqns:
                    trials_in[f] += 1
                    if is_success: success_in[f] += 1
                else:
                    trials_out[f] += 1
                    if is_success: success_out[f] += 1
        
        # 5. Compute Conditional Dependence
        verified_pos = []
        verified_neg = []
        
        for f in fqns:
            p_in = success_in[f] / trials_in[f] if trials_in[f] > 0 else 0.0
            p_out = success_out[f] / trials_out[f] if trials_out[f] > 0 else 0.0
            
            delta_p = p_in - p_out
            
            ctx = c_map[f]
            ctx.metadata["delta_p"] = round(delta_p, 2)
            ctx.metadata["p_in"] = round(p_in, 2)
            ctx.metadata["p_out"] = round(p_out, 2)
            
            if delta_p > 0.05: # Threshold
                ctx.empirical_relevance = "YES"
                verified_pos.append(ctx)
            else:
                ctx.empirical_relevance = "NO"
                verified_neg.append(ctx)
        
        pair.positive_ctxs = verified_pos
        pair.negative_ctxs = verified_neg
        
        # Check final set sufficiency (using all positives)
        if verified_pos:
            combined_text = "\n\n".join([f"Document {i}: {c.text}" for i, c in enumerate(verified_pos)])
            final_ans = await self._generate_answer(pair, combined_text)
            pair.is_sufficient_set = False
            if final_ans:
                try:
                    if pair.source == "api_understanding":
                        pair.is_sufficient_set = await self._validate_api_understanding(pair, final_ans)
                    elif pair.source == "fix_errors":
                        pair.is_sufficient_set = await self._validate_fix_errors(pair, final_ans)
                except Exception:
                    pass
        else:
            pair.is_sufficient_set = False
            
        return pair

    async def _generate_answer(self, pair: RetrievalPair, context: str) -> Optional[GeneratedAnswer]:
        if pair.source == "api_understanding":
            prompt = f"""You are an expert developer.
Context:
{context[:20000]}

Question: {pair.query}

Instructions:
Answer the question using the provided context. 
You MUST output JSON adhering to this schema:
{{
    "benchmark_type": "api_understanding",
    "rationale": "Explanation...",
    "code": "Code snippet...",
    "fully_qualified_class_name": "Full.Class.Name"
}}
"""
        elif pair.source == "fix_errors":
            prompt = f"""You are an expert developer.
Context:
{context[:20000]}

Task: {pair.query}

Instructions:
Fix the error/implement the requirement using the provided context.
You MUST output JSON adhering to this schema:
{{
    "benchmark_type": "fix_error",
    "rationale": "Explanation...",
    "code": "Full corrected python file content..."
}}
"""
        else:
            return None

        try:
            response = await self.client.aio.models.generate_content(
                model=MOST_POWERFUL_MODEL,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            return GeneratedAnswer(raw_output=response.text)
        except Exception as e:
            # print(f"Generation failed: {e}")
            return None

    async def _validate_api_understanding(self, pair: RetrievalPair, answer: GeneratedAnswer) -> bool:
        gt = pair.ground_truth
        # Construct case
        answers_data = gt.get("answers", [])
        if not answers_data: return False
        
        case = ApiUnderstandingBenchmarkCase(
            id=pair.id,
            question=pair.query,
            category=pair.metadata.get("category", "unknown"),
            rationale="N/A",
            template=AnswerTemplate(gt.get("template", "identifier")),
            answers=[StringMatchAnswer(**a) for a in answers_data],
            file=Path("unknown"),
            benchmark_type=BenchmarkType.API_UNDERSTANDING
        )
        runner = ApiUnderstandingRunner()
        
        try:
            # Use Sanitizer for robust extraction
            answer.output = await self.sanitizer.sanitize(
                answer.raw_output, ApiUnderstandingAnswerOutput
            )
            result, logs, _, _ = await runner.run_benchmark(case, answer)
            return result == BenchmarkResultType.PASS
        except Exception as e:
            print(f"Validation error: {e}")
            return False

    async def _validate_fix_errors(self, pair: RetrievalPair, answer: GeneratedAnswer) -> bool:
        gt = pair.ground_truth
        
        def to_path(p): return Path(p) if p else None

        case = FixErrorBenchmarkCase(
            id=pair.id,
            name=gt.get("name", "unknown"),
            description=gt.get("description", "unknown"),
            test_file=to_path(gt.get("test_file")),
            unfixed_file=to_path(gt.get("unfixed_file")),
            fixed_file=to_path(gt.get("fixed_file")),
            requirements=gt.get("requirements"),
            error_output=gt.get("error_output"),
            benchmark_type=BenchmarkType.FIX_ERROR
        )
        runner = PytestBenchmarkRunner()
        
        try:
            # Use Sanitizer for robust extraction
            answer.output = await self.sanitizer.sanitize(
                answer.raw_output, FixErrorAnswerOutput
            )
            result, logs, _, _ = await runner.run_benchmark(case, answer)
            return result == BenchmarkResultType.PASS
        except Exception as e:
            print(f"FixError Validation error: {e}")
            return False

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
