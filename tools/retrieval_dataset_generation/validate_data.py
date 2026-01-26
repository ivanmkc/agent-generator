#!/usr/bin/env python3
import yaml
import logging
import asyncio
import os
import sys
import random
import time
import json
import math
from typing import List, Dict, Any, Literal, Optional
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from google import genai
from google.genai import types
from tqdm.asyncio import tqdm
from colorama import init, Fore, Style

# Initialize colorama
init()

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from benchmarks.data_models import (
    ApiUnderstandingBenchmarkCase, FixErrorBenchmarkCase, MultipleChoiceBenchmarkCase,
    ApiUnderstandingAnswerOutput, FixErrorAnswerOutput, MultipleChoiceAnswerOutput,
    BenchmarkType, AnswerTemplate, StringMatchAnswer, GeneratedAnswer,
    BenchmarkResultType
)
from benchmarks.benchmark_runner import ApiUnderstandingRunner, PytestBenchmarkRunner, MultipleChoiceRunner
from benchmarks.config import MOST_POWERFUL_MODEL
from benchmarks.parsing.json_sanitizer import JsonSanitizer
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType
from benchmarks.benchmark_candidates import ModelName
from tools.retrieval_dataset_generation.lib import (
    EmbeddingRetriever, RankedTarget, RetrievalDataset, RetrievalCase, 
    RetrievalContext, AbstractRetriever, GoldMinerRetriever, RandomRetriever,
    RetrievalResultMetadata
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Switch to Flash for speed/quota
GENERATION_MODEL = ModelName.GEMINI_2_5_FLASH

class DataValidator:
    def __init__(self, input_path: str, output_path: str, retrievers: List[AbstractRetriever]):
        self.input_path = input_path
        self.output_path = output_path
        self.api_key_manager = API_KEY_MANAGER
        self.sanitizer = JsonSanitizer(api_key_manager=self.api_key_manager, model_name=MOST_POWERFUL_MODEL)
        self.retrievers = retrievers
        
    async def validate_dataset(
        self, 
        max_cases: Optional[int] = None, 
        offset: int = 0,
        mode: Literal["fixed", "adaptive"] = "fixed",
        max_n: int = 10,
        min_n: int = 3,
        se_threshold: float = 0.1
    ):
        with open(self.input_path, 'r') as f:
            dataset = RetrievalDataset.model_validate(yaml.safe_load(f))
        
        cases_to_process = dataset.cases[offset:offset+max_cases] if max_cases else dataset.cases[offset:]
        print(f"{Fore.CYAN}Validating {len(cases_to_process)} cases using {GENERATION_MODEL} (Mode: {mode})...{Style.RESET_ALL}")
        
        results = []
        for case in cases_to_process:
            result = await self.validate_case(case, mode=mode, max_n=max_n, min_n=min_n, se_threshold=se_threshold)
            results.append(result)
            
        dataset.cases = results
        
        # Save
        print(f"\n{Fore.GREEN}Saving verified dataset to {self.output_path}...{Style.RESET_ALL}")
        with open(self.output_path, 'w') as f:
            yaml.dump(dataset.model_dump(by_alias=True), f, sort_keys=False, allow_unicode=True)

    async def _generate_candidate_pool(self, case: RetrievalCase) -> List[RetrievalContext]:
        """
        Generates candidate pool using configured retrievers.
        """
        pool = {} 
        print(f"  {Fore.YELLOW}Generating candidate pool for {case.id}...{Style.RESET_ALL}")
        
        for retriever in self.retrievers:
            k = 5
            if isinstance(retriever, GoldMinerRetriever): k = 100
            elif isinstance(retriever, EmbeddingRetriever): k = 15
            elif isinstance(retriever, RandomRetriever): k = 5
                
            results = await retriever.search(case.query, top_k=k, case=case)
            source_name = type(retriever).__name__
            print(f"    - {source_name}: found {len(results)} candidates")
            
            for t in results:
                if t.id not in pool:
                    pool[t.id] = RetrievalContext(
                        fqn=t.id, 
                        text=t.docstring, 
                        type="retrieved"
                    )
        
        print(f"    {Fore.BLUE}Total deduplicated candidates: {len(pool)}{Style.RESET_ALL}")
        return list(pool.values())

    async def validate_case(
        self, 
        case: RetrievalCase,
        mode: str = "fixed",
        max_n: int = 10,
        min_n: int = 3,
        se_threshold: float = 0.1
    ) -> RetrievalCase:
        print(f"\n{Fore.MAGENTA}>>> Processing Case: {case.id}{Style.RESET_ALL}")
        
        # 1. Generate Candidate Pool
        candidates = await self._generate_candidate_pool(case)
        case.candidates = candidates 
        
        if not candidates:
            print(f"    {Fore.RED}No candidates found. Skipping.{Style.RESET_ALL}")
            return case

        c_map = {c.fqn: c for c in candidates}
        fqns = list(c_map.keys())
        
        trials_in = {f: 0 for f in fqns}
        success_in = {f: 0 for f in fqns}
        trials_out = {f: 0 for f in fqns}
        success_out = {f: 0 for f in fqns}
        
        print(f"  {Fore.YELLOW}Running trials (Max: {max_n}, Mode: {mode})...{Style.RESET_ALL}")
        
        for i in range(max_n):
            subset_fqns = [f for f in fqns if random.random() > 0.5]
            if not subset_fqns: subset_fqns = [random.choice(fqns)]
            
            subset_ctxs = [c_map[f] for f in subset_fqns]
            combined_text = "\n\n".join([f"[START_DOCUMENT: {f}]\n{c_map[f].text}\n[END_DOCUMENT]" for f in subset_fqns])
            
            is_success = False
            generated_answer = await self._generate_answer_with_retry(case, combined_text)
            
            if generated_answer:
                try:
                    if case.source == "api_understanding":
                        is_success = await self._validate_api_understanding(case, generated_answer)
                    elif case.source == "fix_errors":
                        is_success = await self._validate_fix_errors(case, generated_answer)
                    elif case.source == "multiple_choice":
                        is_success = await self._validate_multiple_choice(case, generated_answer)
                except Exception:
                    is_success = False
            
            status_char = f"{Fore.GREEN}PASS{Style.RESET_ALL}" if is_success else f"{Fore.RED}FAIL{Style.RESET_ALL}"
            print(f"    Trial {i+1}/{max_n}: {status_char} (Context size: {len(subset_fqns)})")
            
            for f in fqns:
                if f in subset_fqns:
                    trials_in[f] += 1
                    if is_success: success_in[f] += 1
                else:
                    trials_out[f] += 1
                    if is_success: success_out[f] += 1
            
            # Adaptive Stopping Check
            if mode == "adaptive" and i >= min_n - 1:
                if self._check_convergence(fqns, trials_in, success_in, trials_out, success_out, se_threshold):
                    print(f"    {Fore.GREEN}Statistical convergence reached at trial {i+1}. Stopping early.{Style.RESET_ALL}")
                    break
        
        print(f"  {Fore.YELLOW}Calculating impact scores...{Style.RESET_ALL}")
        verified_pos = []
        verified_neg = []
        
        for f in fqns:
            n_in = trials_in[f]
            n_out = trials_out[f]
            
            p_in = success_in[f] / n_in if n_in > 0 else 0.0
            p_out = success_out[f] / n_out if n_out > 0 else 0.0
            
            delta_p = p_in - p_out
            
            se_in = math.sqrt(p_in * (1 - p_in) / n_in) if n_in > 0 else 0.0
            se_out = math.sqrt(p_out * (1 - p_out) / n_out) if n_out > 0 else 0.0
            
            ctx = c_map[f]
            ctx.metadata = RetrievalResultMetadata(
                delta_p=round(delta_p, 2),
                p_in=round(p_in, 2),
                p_out=round(p_out, 2),
                n_in=n_in,
                n_out=n_out,
                se_in=round(se_in, 3),
                se_out=round(se_out, 3)
            )
            
            if delta_p > 0.05:
                ctx.empirical_relevance = "YES"
                verified_pos.append(ctx)
                print(f"    {Fore.GREEN}[+] {f:<60} Delta P: {delta_p:+.2f} (SE: {se_in:.2f}){Style.RESET_ALL}")
            else:
                ctx.empirical_relevance = "NO"
                verified_neg.append(ctx)
        
        case.positive_ctxs = verified_pos
        case.negative_ctxs = verified_neg
        
        if verified_pos:
            combined_text = "\n\n".join([f"[START_DOCUMENT: {c.fqn}]\n{c.text}\n[END_DOCUMENT]" for c in verified_pos])
            final_ans = await self._generate_answer_with_retry(case, combined_text)
            case.is_sufficient_set = False
            if final_ans:
                try:
                    if case.source == "api_understanding":
                        case.is_sufficient_set = await self._validate_api_understanding(case, final_ans)
                    elif case.source == "fix_errors":
                        case.is_sufficient_set = await self._validate_fix_errors(case, final_ans)
                    elif case.source == "multiple_choice":
                        case.is_sufficient_set = await self._validate_multiple_choice(case, final_ans)
                except Exception: pass
            
            suff_color = Fore.GREEN if case.is_sufficient_set else Fore.RED
            print(f"  {Fore.YELLOW}Final Set Sufficiency: {suff_color}{case.is_sufficient_set}{Style.RESET_ALL}")
            
        return case

    def _check_convergence(self, fqns, trials_in, success_in, trials_out, success_out, threshold):
        """
        Check if the Standard Error for the Delta P of top candidates has converged.
        """
        max_se = 0.0
        for f in fqns:
            if trials_in[f] == 0 or trials_out[f] == 0:
                return False # Need at least one sample in each bucket
            
            p_in = success_in[f] / trials_in[f]
            p_out = success_out[f] / trials_out[f]
            
            se_in = math.sqrt(p_in * (1 - p_in) / trials_in[f])
            se_out = math.sqrt(p_out * (1 - p_out) / trials_out[f])
            
            # Combined Standard Error for the difference
            se_diff = math.sqrt(se_in**2 + se_out**2)
            max_se = max(max_se, se_diff)
            
        # If the largest uncertainty in our impact scores is below threshold, we've converged.
        return max_se < threshold

    async def _generate_answer_with_retry(self, case: RetrievalCase, context: str) -> Optional[GeneratedAnswer]:
        """
        Generates answer with retry logic for quota limits.
        """
        target_schema = None
        if case.source == "api_understanding":
            target_schema = ApiUnderstandingAnswerOutput
        elif case.source == "fix_errors":
            target_schema = FixErrorAnswerOutput
        elif case.source == "multiple_choice":
            target_schema = MultipleChoiceAnswerOutput
        else: 
            return None

        # Inject schema definition into prompt
        schema_json = json.dumps(target_schema.model_json_schema(), indent=2)
        
        # Prepare Question Text for MC
        question_text = case.query
        if case.source == "multiple_choice":
            options = case.metadata.get("options", {})
            if options:
                opt_str = "\n".join([f"{k}: {v}" for k, v in options.items()])
                question_text = f"{case.query}\n\nOptions:\n{opt_str}"

        prompt = f"""You are an expert developer.
Context:
{context[:30000]}

Task: {question_text}

Instructions:
1. Answer the question using ONLY the provided context.
2. You MUST output a valid JSON object matching the schema below.

Target Schema:
{schema_json}
"""

        max_retries = 3
        backoff = 5
        
        for attempt in range(max_retries):
            # Get a fresh key for each attempt
            key_val, key_id = await self.api_key_manager.get_next_key_with_id(KeyType.GEMINI_API)
            if not key_val:
                print(f"    {Fore.RED}No API keys available.{Style.RESET_ALL}")
                return None
                
            client = genai.Client(api_key=key_val)
            
            try:
                # Use response_schema in config for enforcement
                response = await client.aio.models.generate_content(
                    model=GENERATION_MODEL,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": target_schema
                    }
                )
                
                # Report success
                await self.api_key_manager.report_result(KeyType.GEMINI_API, key_id, True)
                return GeneratedAnswer(raw_output=response.text)
                
            except Exception as e:
                error_msg = str(e)
                # Report failure
                await self.api_key_manager.report_result(KeyType.GEMINI_API, key_id, False, error_message=error_msg)
                
                if "429" in error_msg or "ResourceExhausted" in error_msg:
                    wait_time = backoff * (2 ** attempt)
                    print(f"    {Fore.YELLOW}Quota exceeded (429). Retrying in {wait_time}s...{Style.RESET_ALL}")
                    await asyncio.sleep(wait_time)
                else:
                    # print(f"    {Fore.RED}Generation failed: {e}{Style.RESET_ALL}")
                    return None
                    
        return None

    async def _validate_api_understanding(self, case: RetrievalCase, answer: GeneratedAnswer) -> bool:
        gt = case.ground_truth
        if not gt.get("answers"): return False
        bcase = ApiUnderstandingBenchmarkCase(
            id=case.id, question=case.query, category=case.metadata.get("category", "unknown"),
            rationale="N/A", template=AnswerTemplate(gt.get("template", "identifier")),
            answers=[StringMatchAnswer(**a) for a in gt.get("answers", [])],
            file=Path("unknown"), benchmark_type=BenchmarkType.API_UNDERSTANDING
        )
        runner = ApiUnderstandingRunner()
        try:
            answer.output = await self.sanitizer.sanitize(answer.raw_output, ApiUnderstandingAnswerOutput)
            result, _, _, _ = await runner.run_benchmark(bcase, answer)
            return result == BenchmarkResultType.PASS
        except Exception as e: 
            print(f"      {Fore.RED}API Validation Error: {e}{Style.RESET_ALL}")
            return False

    async def _validate_fix_errors(self, case: RetrievalCase, answer: GeneratedAnswer) -> bool:
        gt = case.ground_truth
        def to_path(p): return Path(p) if p else None
        bcase = FixErrorBenchmarkCase(
            id=case.id, name=gt.get("name", "unknown"), description=gt.get("description", "unknown"),
            test_file=to_path(gt.get("test_file")), unfixed_file=to_path(gt.get("unfixed_file")),
            fixed_file=to_path(gt.get("fixed_file")), requirements=gt.get("requirements"),
            error_output=gt.get("error_output"), benchmark_type=BenchmarkType.FIX_ERROR
        )
        runner = PytestBenchmarkRunner()
        try:
            answer.output = await self.sanitizer.sanitize(answer.raw_output, FixErrorAnswerOutput)
            result, logs, _, _ = await runner.run_benchmark(bcase, answer)
            return result == BenchmarkResultType.PASS
        except Exception as e: 
            print(f"      {Fore.RED}FixError Validation Error: {e}{Style.RESET_ALL}")
            return False

    async def _validate_multiple_choice(self, case: RetrievalCase, answer: GeneratedAnswer) -> bool:
        gt = case.ground_truth
        bcase = MultipleChoiceBenchmarkCase(
            id=case.id,
            question=case.query,
            options=gt.get("options", {}),
            correct_answer=gt.get("correct_answer"),
            explanation=gt.get("explanation"),
            benchmark_type=BenchmarkType.MULTIPLE_CHOICE
        )
        runner = MultipleChoiceRunner()
        try:
            answer.output = await self.sanitizer.sanitize(answer.raw_output, MultipleChoiceAnswerOutput)
            result, _, _, _ = await runner.run_benchmark(bcase, answer)
            return result == BenchmarkResultType.PASS
        except Exception as e: 
            print(f"      {Fore.RED}MC Validation Error: {e}{Style.RESET_ALL}")
            return False

if __name__ == "__main__":
    # Pre-fetch a key for embeddings
    key_val = asyncio.run(API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API))
    if not key_val:
        print("No API key available for Embedding Retriever initialization.")
        exit(1)
        
    targets_path = "benchmarks/benchmark_generator/data/ranked_targets.yaml"
    
    print(f"{Fore.CYAN}Initializing Retrievers...{Style.RESET_ALL}")
    with open(targets_path, 'r') as f:
        raw_targets = yaml.safe_load(f)
        if not isinstance(raw_targets, list): raw_targets = raw_targets.get('targets', [])
        targets = [RankedTarget(id=t['id'], name=t['name'], docstring=t.get('docstring', '')) for t in raw_targets if t.get('id')]
    
    gold_miner = GoldMinerRetriever(); asyncio.run(gold_miner.index(targets))
    random_retriever = RandomRetriever(); asyncio.run(random_retriever.index(targets))
    embedding_retriever = EmbeddingRetriever(api_key=key_val); asyncio.run(embedding_retriever.index(targets))
    
    validator = DataValidator(
        "retrieval_dataset.yaml", "retrieval_dataset_verified.yaml",
        retrievers=[gold_miner, embedding_retriever, random_retriever]
    )
    # Run on full dataset
    asyncio.run(validator.validate_dataset())
