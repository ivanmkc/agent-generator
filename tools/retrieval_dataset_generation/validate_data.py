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
import argparse
from datetime import datetime
from typing import List, Dict, Any, Literal, Optional, Union, Tuple
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
    RetrievalResultMetadata, ValidatorConfig,
    BaseLogEvent, TrialCompleteEvent, ConvergenceCheckEvent, ValidationStartEvent, 
    PoolGeneratedEvent, PoolingViolationEvent
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Switch to Flash for speed/quota
GENERATION_MODEL = ModelName.GEMINI_2_5_FLASH

class DataValidator:
    def __init__(self, input_path: str, output_path: str, retrievers: List[AbstractRetriever], config: Optional[ValidatorConfig] = None):
        self.input_path = input_path
        self.output_path = output_path
        self.api_key_manager = API_KEY_MANAGER
        self.sanitizer = JsonSanitizer(api_key_manager=self.api_key_manager, model_name=MOST_POWERFUL_MODEL)
        self.retrievers = retrievers
        self.config = config or ValidatorConfig()
        
        # Setup structured logging
        self.log_file = Path(self.config.log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        # Clear log file on start
        if self.log_file.exists():
            with open(self.log_file, 'w') as f:
                pass

    def _log_event(self, event: BaseLogEvent):
        """Writes a structured event to the YAML log."""
        with open(self.log_file, 'a') as f:
            # Use explicit_start=True to create a multi-document YAML stream
            yaml.dump(event.model_dump(), f, explicit_start=True, sort_keys=False)

    async def validate_dataset(
        self,
        max_cases: Optional[int] = None,
        offset: int = 0,
        mode: Literal["fixed", "adaptive"] = "fixed"
    ):
        with open(self.input_path, 'r') as f:
            dataset = RetrievalDataset.model_validate(yaml.safe_load(f))
        
        cases_to_process = dataset.cases[offset:offset+max_cases] if max_cases else dataset.cases[offset:]
        print(f"{Fore.CYAN}Validating {len(cases_to_process)} cases using {GENERATION_MODEL} (Mode: {mode}, Concurrency: {self.config.concurrency})...{Style.RESET_ALL}")
        
        self._log_event(ValidationStartEvent(mode=mode, case_count=len(cases_to_process)))

        results = []
        for case in cases_to_process:
            result = await self.validate_case(case, mode=mode)
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
        print(f"  {Style.DIM}➤ Generating candidate pool...{Style.RESET_ALL}")
        
        for retriever in self.retrievers:
            k = 5
            source_type = "unknown"
            if isinstance(retriever, GoldMinerRetriever): 
                k = self.config.gold_miner_k
                source_type = "gold_mined"
            elif isinstance(retriever, EmbeddingRetriever): 
                k = self.config.vector_search_k
                source_type = "retrieved"
            elif isinstance(retriever, RandomRetriever): 
                k = self.config.random_noise_n
                source_type = "random_noise"
                
            results = await retriever.search(case.query, top_k=k, case=case)
            source_name = type(retriever).__name__
            print(f"    {Style.DIM}• {source_name}: found {len(results)} candidates{Style.RESET_ALL}")
            
            for t in results:
                if t.id not in pool:
                    pool[t.id] = RetrievalContext(
                        fqn=t.id, 
                        text=t.docstring, 
                        type=source_type
                    )
        
        print(f"    {Fore.BLUE}Total deduplicated candidates: {len(pool)}{Style.RESET_ALL}")
        self._log_event(PoolGeneratedEvent(case_id=case.id, pool_size=len(pool)))
        return list(pool.values())

    async def validate_case(
        self, 
        case: RetrievalCase,
        mode: str = "fixed"
    ) -> RetrievalCase:
        print(f"\n{Fore.MAGENTA}▶ Processing Case: {case.id}{Style.RESET_ALL}")
        
        # 1. Zero-Context Baseline
        print(f"  {Fore.CYAN}➤ Running Zero-Context Baseline...{Style.RESET_ALL}")
        baseline_successes = 0
        N_BASELINE = 3
        for i in range(N_BASELINE):
            generated_answer, prompt_used = await self._generate_answer_with_retry(case, "") # Empty context
            if generated_answer is None:
                print(f"    {Style.DIM}• Trial {i+1}: GENERATION_FAILURE{Style.RESET_ALL}")
                continue

            is_correct = False
            try:
                if case.source == "api_understanding":
                    is_correct, _ = await self._validate_api_understanding(case, generated_answer)
                elif case.source == "fix_errors":
                    is_correct, _ = await self._validate_fix_errors(case, generated_answer)
                elif case.source == "multiple_choice":
                    is_correct, _ = await self._validate_multiple_choice(case, generated_answer)
            except Exception:
                is_correct = False
            
            if is_correct:
                baseline_successes += 1
            
            status_char = f"{Fore.GREEN}PASS{Style.RESET_ALL}" if is_correct else f"{Fore.RED}FAIL{Style.RESET_ALL}"
            print(f"    • Trial {i+1}: {status_char}")

        case.metadata['zero_context_success_rate'] = baseline_successes / N_BASELINE
        print(f"    {Fore.BLUE}Baseline Success Rate: {case.metadata['zero_context_success_rate']:.2f}{Style.RESET_ALL}")

        # 2. Generate Candidate Pool
        candidates = await self._generate_candidate_pool(case)
        case.candidates = candidates 
        
        if not candidates:
            print(f"  {Fore.RED}⚠ No candidates found. Skipping.{Style.RESET_ALL}")
            return case

        c_map = {c.fqn: c for c in candidates}
        fqns = list(c_map.keys())
        
        # Shared State for Stats
        trials_in = {f: 0 for f in fqns}
        success_in = {f: 0 for f in fqns}
        trials_out = {f: 0 for f in fqns}
        success_out = {f: 0 for f in fqns}
        
        max_n = self.config.adaptive_max_n if mode == "adaptive" else self.config.monte_carlo_trials
        min_n = self.config.adaptive_min_n if mode == "adaptive" else max_n
        
        print(f"  {Fore.CYAN}➤ Running Monte Carlo Trials (Max: {max_n}, Mode: {mode}, Concurrency: {self.config.concurrency})...{Style.RESET_ALL}")
        
        case.metadata['convergence_trace'] = []
        
        # Concurrency Control
        semaphore = asyncio.Semaphore(self.config.concurrency)
        trials_completed = 0
        stop_signal = False
        
        async def run_single_trial(trial_idx: int):
            nonlocal trials_completed, stop_signal
            if stop_signal: return

            async with semaphore:
                # Double check after acquiring semaphore
                if stop_signal: return

                subset_fqns = [f for f in fqns if random.random() < self.config.sampling_probability]
                combined_text = "\n\n".join([f"[START_DOCUMENT: {f}]\n{c_map[f].text}\n[END_DOCUMENT]" for f in subset_fqns])
                
                generated_answer, prompt_used = await self._generate_answer_with_retry(case, combined_text)
                
                if generated_answer is None:
                    print(f"    {Style.DIM}• Trial {trial_idx+1}: GENERATION_FAILURE (retrying...){Style.RESET_ALL}")
                    # In a real queue we would re-add, but here we just skip updating stats for this index
                    # Ideally we should retry, but for simplicity in concurrency we skip inconclusive trials
                    return 

                is_correct = False
                val_error = None
                try:
                    if case.source == "api_understanding":
                        is_correct, val_error = await self._validate_api_understanding(case, generated_answer)
                    elif case.source == "fix_errors":
                        is_correct, val_error = await self._validate_fix_errors(case, generated_answer)
                    elif case.source == "multiple_choice":
                        is_correct, val_error = await self._validate_multiple_choice(case, generated_answer)
                except Exception as e:
                    is_correct = False
                    val_error = str(e)

                # Log Event
                self._log_event(TrialCompleteEvent(
                    case_id=case.id, trial_index=trial_idx, subset_size=len(subset_fqns),
                    subset_fqns=subset_fqns, is_correct=is_correct,
                    prompt_preview=prompt_used[:500] + "..." if len(prompt_used) > 500 else prompt_used,
                    generated_output=generated_answer.raw_output,
                    validation_error=val_error
                ))

                status_char = f"{Fore.GREEN}PASS{Style.RESET_ALL}" if is_correct else f"{Fore.RED}FAIL{Style.RESET_ALL}"
                print(f"    • Trial {trial_idx+1:<2}/{max_n}: {status_char} (Ctx: {len(subset_fqns)})")
                
                # Update Stats (Thread-safe in asyncio single loop)
                for f in fqns:
                    if f in subset_fqns:
                        trials_in[f] += 1
                        if is_correct: success_in[f] += 1
                    else:
                        trials_out[f] += 1
                        if is_correct: success_out[f] += 1
                
                trials_completed += 1
                
                # Check Convergence
                max_se_diff = 0.0
                se_map = {}
                for f in fqns:
                    if trials_in[f] > 0 and trials_out[f] > 0:
                        p_in = success_in[f] / trials_in[f]
                        p_out = success_out[f] / trials_out[f]
                        
                        se_in = math.sqrt(p_in * (1 - p_in) / trials_in[f]) if (0 < p_in < 1) else (1.0 / trials_in[f])
                        se_out = math.sqrt(p_out * (1 - p_out) / trials_out[f]) if (0 < p_out < 1) else (1.0 / trials_out[f])
                        se_diff = math.sqrt(se_in**2 + se_out**2)
                        max_se_diff = max(max_se_diff, se_diff)
                        se_map[f] = round(se_diff, 4)
                    else:
                        max_se_diff = 1.0
                        se_map[f] = 1.0
                
                case.metadata['convergence_trace'].append(max_se_diff)
                self._log_event(ConvergenceCheckEvent(
                    case_id=case.id, trial_index=trial_idx, max_se_diff=max_se_diff,
                    se_map=se_map, threshold=self.config.se_threshold
                ))

                if mode == "adaptive" and trials_completed >= min_n:
                    if self._check_convergence(fqns, trials_in, success_in, trials_out, success_out, self.config.se_threshold):
                        print(f"      {Fore.GREEN}✔ Convergence reached (Trial {trial_idx+1}). Stopping.{Style.RESET_ALL}")
                        stop_signal = True

        # Launch Tasks
        tasks = [run_single_trial(i) for i in range(max_n)]
        await asyncio.gather(*tasks)
        
        print(f"  {Fore.CYAN}➤ Impact Scores:{Style.RESET_ALL}")
        
        for f in fqns:
            n_in, n_out = trials_in[f], trials_out[f]
            p_in = success_in[f] / n_in if n_in > 0 else 0.0
            p_out = success_out[f] / n_out if n_out > 0 else 0.0
            delta_p = p_in - p_out
            se_in = math.sqrt(p_in * (1 - p_in) / n_in) if n_in > 0 else 0.0
            
            ctx = c_map[f]
            ctx.metadata = RetrievalResultMetadata(
                delta_p=round(delta_p, 2), p_in=round(p_in, 2), p_out=round(p_out, 2),
                n_in=n_in, n_out=n_out, se_in=round(se_in, 3)
            )
            
            color = Fore.GREEN if delta_p > 0.1 else (Fore.RED if delta_p < -0.1 else Fore.WHITE)
            print(f"    [{delta_p:+.2f}] {color}{f:<60}{Style.RESET_ALL} (SE: {se_in:.2f})")

            if ctx.context_type == "random_noise" and delta_p > 0.1:
                print(f"      {Fore.RED}⚠ Pooling Violation: Random doc found relevant!{Style.RESET_ALL}")
                self._log_event(PoolingViolationEvent(case_id=case.id, fqn=f, delta_p=delta_p))
        
        # Check final set sufficiency
        if candidates:
            combined_text = "\n\n".join([f"[START_DOCUMENT: {c.fqn}]\n{c.text}\n[END_DOCUMENT]" for c in candidates])
            final_ans, _ = await self._generate_answer_with_retry(case, combined_text)
            case.is_sufficient_set = False
            if final_ans:
                try:
                    if case.source == "api_understanding":
                        case.is_sufficient_set, _ = await self._validate_api_understanding(case, final_ans)
                    elif case.source == "fix_errors":
                        case.is_sufficient_set, _ = await self._validate_fix_errors(case, final_ans)
                    elif case.source == "multiple_choice":
                        case.is_sufficient_set, _ = await self._validate_multiple_choice(case, final_ans)
                except Exception: pass
            
            suff_color = Fore.GREEN if case.is_sufficient_set else Fore.RED
            print(f"  {Fore.CYAN}➤ Total Pool Sufficiency: {suff_color}{case.is_sufficient_set}{Style.RESET_ALL}")
            
        return case

    def _check_convergence(self, fqns, trials_in, success_in, trials_out, success_out, threshold):
        max_se = 0.0
        for f in fqns:
            if trials_in[f] == 0 or trials_out[f] == 0:
                return False 
            p_in = success_in[f] / trials_in[f]
            p_out = success_out[f] / trials_out[f]
            se_in = math.sqrt(p_in * (1 - p_in) / trials_in[f]) if (0 < p_in < 1) else (1.0 / trials_in[f])
            se_out = math.sqrt(p_out * (1 - p_out) / trials_out[f]) if (0 < p_out < 1) else (1.0 / trials_out[f])
            se_diff = math.sqrt(se_in**2 + se_out**2)
            max_se = max(max_se, se_diff)
        return max_se < threshold

    async def _generate_answer_with_retry(self, case: RetrievalCase, context: str) -> Tuple[Optional[GeneratedAnswer], str]:
        target_schema = None
        if case.source == "api_understanding":
            target_schema = ApiUnderstandingAnswerOutput
        elif case.source == "fix_errors":
            target_schema = FixErrorAnswerOutput
        elif case.source == "multiple_choice":
            target_schema = MultipleChoiceAnswerOutput
        else: 
            return None, ""

        schema_json = json.dumps(target_schema.model_json_schema(), indent=2)
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
            key_val, key_id = await self.api_key_manager.get_next_key_with_id(KeyType.GEMINI_API)
            if not key_val:
                print(f"    {Fore.RED}No API keys available.{Style.RESET_ALL}")
                return None, prompt
                
            client = genai.Client(api_key=key_val)
            
            try:
                response = await client.aio.models.generate_content(
                    model=GENERATION_MODEL,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": target_schema
                    }
                )
                await self.api_key_manager.report_result(KeyType.GEMINI_API, key_id, True)
                return GeneratedAnswer(raw_output=response.text), prompt
                
            except Exception as e:
                error_msg = str(e)
                await self.api_key_manager.report_result(KeyType.GEMINI_API, key_id, False, error_message=error_msg)
                
                if "429" in error_msg or "ResourceExhausted" in error_msg:
                    wait_time = backoff * (2 ** attempt)
                    print(f"    {Fore.YELLOW}Quota exceeded (429). Retrying in {wait_time}s...{Style.RESET_ALL}")
                    await asyncio.sleep(wait_time)
                else:
                    return None, prompt
                    
        return None, prompt

    async def _validate_api_understanding(self, case: RetrievalCase, answer: GeneratedAnswer) -> Tuple[bool, Optional[str]]:
        gt = case.ground_truth
        if not gt.get("answers"): return False, "No ground truth answers"
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
            return result == BenchmarkResultType.PASS, None
        except Exception as e: 
            return False, str(e)

    async def _validate_fix_errors(self, case: RetrievalCase, answer: GeneratedAnswer) -> Tuple[bool, Optional[str]]:
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
            error_msg = None if result == BenchmarkResultType.PASS else f"Runner Result: {result}, Logs: {logs}"
            return result == BenchmarkResultType.PASS, error_msg
        except Exception as e: 
            return False, str(e)

    async def _validate_multiple_choice(self, case: RetrievalCase, answer: GeneratedAnswer) -> Tuple[bool, Optional[str]]:
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
            error_msg = None if result == BenchmarkResultType.PASS else f"Wrong Answer. Expected {gt.get('correct_answer')}, Got {answer.output.answer}"
            return result == BenchmarkResultType.PASS, error_msg
        except Exception as e: 
            return False, str(e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieval Data Validator")
    parser.add_argument("--input", default="retrieval_dataset.yaml", help="Input dataset path")
    parser.add_argument("--output", default="retrieval_dataset_verified.yaml", help="Output dataset path")
    parser.add_argument("--log-dir", default="logs", help="Directory for logs")
    parser.add_argument("--mode", default="adaptive", choices=["fixed", "adaptive"], help="Sampling mode")
    parser.add_argument("--max-cases", type=int, default=None, help="Limit number of cases")
    
    args = parser.parse_args()
    
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
    
    # Generate timestamped log path
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = Path(args.log_dir) / f"validation_run_{timestamp}.yaml"
    
    # Config
    config = ValidatorConfig(log_file=str(log_file))
    
    validator = DataValidator(
        args.input, args.output,
        retrievers=[gold_miner, embedding_retriever, random_retriever],
        config=config
    )
    # Run
    asyncio.run(validator.validate_dataset(max_cases=args.max_cases, mode=args.mode))