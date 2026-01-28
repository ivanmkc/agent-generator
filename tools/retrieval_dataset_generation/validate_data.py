#!/usr/bin/env python3
"""Validate Data module."""

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
    ApiUnderstandingBenchmarkCase,
    FixErrorBenchmarkCase,
    MultipleChoiceBenchmarkCase,
    ApiUnderstandingAnswerOutput,
    FixErrorAnswerOutput,
    MultipleChoiceAnswerOutput,
    BenchmarkType,
    AnswerTemplate,
    StringMatchAnswer,
    GeneratedAnswer,
    BenchmarkResultType,
)
from benchmarks.benchmark_runner import ApiUnderstandingRunner, PytestBenchmarkRunner, MultipleChoiceRunner
from core.config import MOST_POWERFUL_MODEL
from benchmarks.parsing.json_sanitizer import JsonSanitizer
from core.api_key_manager import API_KEY_MANAGER, KeyType
from core.models import ModelName
from tools.retrieval_dataset_generation.retrieval_engine import (
    EmbeddingRetriever,
    RankedTarget,
    RetrievalDataset,
    RetrievalCase,
    RetrievalContext,
    AbstractRetriever,
    GoldMinerRetriever,
    RandomRetriever,
    RetrievalResultMetadata,
    ValidatorConfig,
    BaseLogEvent,
    TrialCompleteEvent,
    ConvergenceCheckEvent,
    ValidationStartEvent,
    PoolGeneratedEvent,
    PoolingViolationEvent,
    CaseSkippedEvent,
    CandidateDowngradedEvent,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Suppress AFC noise from google-genai
logging.getLogger("google_genai.models").setLevel(logging.WARNING)

# Switch to Pro for higher reasoning capability as requested
GENERATION_MODEL = ModelName.GEMINI_2_5_PRO


class DataValidator:
    """
    Main engine for validating retrieval datasets using Monte Carlo causal inference.

    The validator determines the empirical relevance of documents for a given query
    by measuring the "lift" in success probability (Delta P) when a document is
    present in the context vs when it is absent.
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        retrievers: List[AbstractRetriever],
        config: Optional[ValidatorConfig] = None,
    ):
        self.input_path = input_path
        self.output_path = output_path
        self.api_key_manager = API_KEY_MANAGER
        self.sanitizer = JsonSanitizer(
            api_key_manager=self.api_key_manager, model_name=MOST_POWERFUL_MODEL
        )
        self.retrievers = retrievers
        self.config = config or ValidatorConfig()

        # Setup structured logging
        self.log_file = Path(self.config.log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        # Clear log file on start
        if self.log_file.exists():
            with open(self.log_file, "w") as f:
                pass

    def _log_event(self, event: BaseLogEvent):
        """Writes a structured event to the YAML log for later forensic analysis."""
        with open(self.log_file, "a") as f:
            yaml.dump(event.model_dump(), f, explicit_start=True, sort_keys=False)

    async def validate_dataset(
        self,
        max_cases: Optional[int] = None,
        offset: int = 0,
        mode: Literal["fixed", "adaptive"] = "fixed",
    ):
        """
        Processes a batch of cases from the input dataset.
        Supports resuming from intermediate results stored in output_path.
        """
        with open(self.input_path, "r") as f:
            dataset = RetrievalDataset.model_validate(yaml.safe_load(f))

        # Resume Logic: Load existing output if it exists
        existing_results = {}
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, "r") as f:
                    existing_data = yaml.safe_load(f)
                    if existing_data:
                        existing_dataset = RetrievalDataset.model_validate(
                            existing_data
                        )
                        existing_results = {c.id: c for c in existing_dataset.cases}
                        print(
                            f"{Fore.YELLOW}Resuming: Found {len(existing_results)} existing verified cases in {self.output_path}{Style.RESET_ALL}"
                        )
            except Exception as e:
                print(
                    f"{Fore.RED}Error loading existing output for resume: {e}. Starting fresh.{Style.RESET_ALL}"
                )

        cases_to_process = (
            dataset.cases[offset : offset + max_cases]
            if max_cases
            else dataset.cases[offset:]
        )
        print(
            f"{Fore.CYAN}Validating {len(cases_to_process)} cases using {GENERATION_MODEL} (Mode: {mode}, Concurrency: {self.config.concurrency})...{Style.RESET_ALL}"
        )

        self._log_event(
            ValidationStartEvent(mode=mode, case_count=len(cases_to_process))
        )

        results = list(existing_results.values())
        completed_ids = set(existing_results.keys())

        for case in cases_to_process:
            if case.id in completed_ids:
                print(
                    f"  {Style.DIM}➤ Skipping already completed case: {case.id}{Style.RESET_ALL}"
                )
                continue

            result = await self.validate_case(case, mode=mode)
            results.append(result)
            completed_ids.add(case.id)

            # Save intermediate results after each case
            dataset.cases = results
            with open(self.output_path, "w") as f:
                yaml.dump(
                    dataset.model_dump(by_alias=True),
                    f,
                    sort_keys=False,
                    allow_unicode=True,
                )
            print(
                f"  {Style.DIM}➤ Intermediate results saved to {self.output_path}{Style.RESET_ALL}"
            )

        dataset.cases = results

        print(
            f"\n{Fore.GREEN}Finished. Final verified dataset saved to {self.output_path}...{Style.RESET_ALL}"
        )

    async def _generate_candidate_pool(
        self, case: RetrievalCase
    ) -> List[RetrievalContext]:
        """
        Aggregates potential documents from all retrievers (Gold, Vector, Random).
        This forms the unified pool for Monte Carlo sampling.
        """
        pool = {}
        print(f"  {Style.DIM}➤ Generating candidate pool...{Style.RESET_ALL}")

        for retriever in self.retrievers:
            k = 5
            source_type = "unknown"
            # TODO: Do not use isinstance, instead modify AbstractRetriever to have a 'configured_k' and 'source_type' property
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
            print(
                f"    {Style.DIM}• {source_name}: found {len(results)} candidates{Style.RESET_ALL}"
            )

            for t in results:
                if t.id not in pool:
                    pool[t.id] = RetrievalContext(
                        fqn=t.id, text=t.docstring, type=source_type
                    )

        print(
            f"    {Fore.BLUE}Total deduplicated candidates: {len(pool)}{Style.RESET_ALL}"
        )
        self._log_event(PoolGeneratedEvent(case_id=case.id, pool_size=len(pool)))

        # TODO: Randomize candidates
        return list(pool.values())

    async def validate_case(
        self, case: RetrievalCase, mode: str = "fixed"
    ) -> RetrievalCase:
        """
        Orchestrates the validation of a single case:
        1. Runs zero-context baseline to check for memorization.
        2. Generates a randomized candidate pool.
        3. Runs Monte Carlo trials using randomized subsets of the pool.
        4. Calculates Delta P (impact score) for each document.
        5. Performs a final sufficiency check with the full pool.
        """
        print(f"\n{Fore.MAGENTA}▶ Processing Case: {case.id}{Style.RESET_ALL}")

        # 1. Zero-Context Baseline
        print(f"  {Fore.CYAN}➤ Running Zero-Context Baseline...{Style.RESET_ALL}")

        # Calculate random guessing threshold
        guessing_threshold = 0.0
        if case.source == "multiple_choice":
            num_options = len(case.ground_truth.get("options", {}))
            if num_options > 0:
                guessing_threshold = 1.0 / num_options

        baseline_successes = 0
        N_BASELINE = 10
        for i in range(N_BASELINE):
            generated_answer, prompt_used = await self._generate_answer_with_retry(
                case, ""
            )
            if generated_answer is None:
                print(
                    f"    {Style.DIM}• Trial {i+1}: GENERATION_FAILURE{Style.RESET_ALL}"
                )
                continue

            is_correct = False
            try:
                if case.source == "api_understanding":
                    is_correct, _ = await self._validate_api_understanding(
                        case, generated_answer
                    )
                elif case.source == "fix_errors":
                    is_correct, val_error = await self._validate_fix_errors(
                        case, generated_answer
                    )
                elif case.source == "multiple_choice":
                    is_correct, val_error = await self._validate_multiple_choice(
                        case, generated_answer
                    )
            except Exception:
                is_correct = False

            if is_correct:
                baseline_successes += 1

            status_char = (
                f"{Fore.GREEN}PASS{Style.RESET_ALL}"
                if is_correct
                else f"{Fore.RED}FAIL{Style.RESET_ALL}"
            )
            print(f"    • Trial {i+1}: {status_char}")

        baseline_rate = baseline_successes / N_BASELINE
        case.metadata["zero_context_success_rate"] = baseline_rate
        print(
            f"    {Fore.BLUE}Baseline Success Rate: {baseline_rate:.2f} (Threshold: {guessing_threshold:.2f}){Style.RESET_ALL}"
        )

        if baseline_rate > guessing_threshold:
            print(
                f"  {Fore.YELLOW}⚠ Skipping Case: Solvable without context (Rate {baseline_rate:.2f} > Threshold {guessing_threshold:.2f}){Style.RESET_ALL}"
            )
            self._log_event(
                CaseSkippedEvent(
                    case_id=case.id,
                    reason="Solvable without context",
                    baseline_success_rate=baseline_rate,
                    threshold=guessing_threshold,
                )
            )
            case.metadata["skipped"] = True
            return case

        # 2. Generate Candidate Pool
        candidates = await self._generate_candidate_pool(case)
        case.candidates = candidates

        if not candidates:
            print(f"  {Fore.RED}⚠ No candidates found. Skipping.{Style.RESET_ALL}")
            return case

        c_map = {c.fqn: c for c in candidates}
        fqns = list(c_map.keys())

        trials_in = {f: 0 for f in fqns}
        success_in = {f: 0 for f in fqns}
        trials_out = {f: 0 for f in fqns}
        success_out = {f: 0 for f in fqns}

        max_n = (
            self.config.adaptive_max_n
            if mode == "adaptive"
            else self.config.monte_carlo_trials
        )
        min_n = self.config.adaptive_min_n if mode == "adaptive" else max_n

        print(
            f"  {Fore.CYAN}➤ Running Monte Carlo Trials (Max: {max_n}, Mode: {mode}, Concurrency: {self.config.concurrency})...{Style.RESET_ALL}"
        )

        case.metadata["convergence_trace"] = []
        semaphore = asyncio.Semaphore(self.config.concurrency)
        trials_completed = 0
        stop_signal = False

        async def run_single_trial(trial_idx: int):
            """
            Runs a single trial with a random subset of documents.
            Updates stats and checks for early termination (convergence).
            """
            nonlocal trials_completed, stop_signal
            if stop_signal:
                return

            async with semaphore:
                if stop_signal:
                    return

                # Dynamic Sampling: Reduce probability for converged docs
                active_subset_fqns = []
                for f in fqns:
                    prob = self.config.sampling_probability
                    # Check if this specific doc has already converged
                    if trials_in[f] > 0 and trials_out[f] > 0:
                        p_in = success_in[f] / trials_in[f]
                        p_out = success_out[f] / trials_out[f]
                        se_in = (
                            math.sqrt(p_in * (1 - p_in) / trials_in[f])
                            if (0 < p_in < 1)
                            else (1.0 / trials_in[f])
                        )
                        se_out = (
                            math.sqrt(p_out * (1 - p_out) / trials_out[f])
                            if (0 < p_out < 1)
                            else (1.0 / trials_out[f])
                        )
                        se_diff = math.sqrt(se_in**2 + se_out**2)
                        if se_diff < self.config.se_threshold:
                            prob /= 5.0  # Lower pick rate for converged docs

                    if random.random() < prob:
                        active_subset_fqns.append(f)

                combined_text = "\n\n".join(
                    [
                        f"[START_DOCUMENT: {f}]\n{c_map[f].text}\n[END_DOCUMENT]"
                        for f in active_subset_fqns
                    ]
                )

                generated_answer, prompt_used = await self._generate_answer_with_retry(
                    case, combined_text
                )

                if generated_answer is None:
                    print(
                        f"    {Style.DIM}• Trial {trial_idx+1}: GENERATION_FAILURE (skipping...){Style.RESET_ALL}"
                    )
                    return

                is_correct = False
                val_error = None
                try:
                    if case.source == "api_understanding":
                        is_correct, val_error = await self._validate_api_understanding(
                            case, generated_answer
                        )
                    elif case.source == "fix_errors":
                        is_correct, val_error = await self._validate_fix_errors(
                            case, generated_answer
                        )
                    elif case.source == "multiple_choice":
                        is_correct, val_error = await self._validate_multiple_choice(
                            case, generated_answer
                        )
                except Exception as e:
                    is_correct = False
                    val_error = str(e)

                self._log_event(
                    TrialCompleteEvent(
                        case_id=case.id,
                        trial_index=trial_idx,
                        subset_size=len(active_subset_fqns),
                        subset_fqns=active_subset_fqns,
                        is_correct=is_correct,
                        prompt_preview=prompt_used[:500] + "..."
                        if len(prompt_used) > 500
                        else prompt_used,
                        generated_output=generated_answer.raw_output,
                        validation_error=val_error,
                    )
                )

                status_char = (
                    f"{Fore.GREEN}PASS{Style.RESET_ALL}"
                    if is_correct
                    else f"{Fore.RED}FAIL{Style.RESET_ALL}"
                )
                print(
                    f"    • Trial {trial_idx+1:<2}/{max_n}: {status_char} (Ctx: {len(active_subset_fqns)})"
                )

                for f in fqns:
                    if f in active_subset_fqns:
                        trials_in[f] += 1
                        if is_correct:
                            success_in[f] += 1
                    else:
                        trials_out[f] += 1
                        if is_correct:
                            success_out[f] += 1

                trials_completed += 1

                max_se_diff = 0.0
                se_map = {}
                converged_count = 0
                for f in fqns:
                    if trials_in[f] > 0 and trials_out[f] > 0:
                        p_in = success_in[f] / trials_in[f]
                        p_out = success_out[f] / trials_out[f]
                        se_in = (
                            math.sqrt(p_in * (1 - p_in) / trials_in[f])
                            if (0 < p_in < 1)
                            else (1.0 / trials_in[f])
                        )
                        se_out = (
                            math.sqrt(p_out * (1 - p_out) / trials_out[f])
                            if (0 < p_out < 1)
                            else (1.0 / trials_out[f])
                        )
                        se_diff = math.sqrt(se_in**2 + se_out**2)
                        max_se_diff = max(max_se_diff, se_diff)
                        se_map[f] = round(se_diff, 4)
                        if se_diff < self.config.se_threshold:
                            converged_count += 1
                    else:
                        max_se_diff = 1.0
                        se_map[f] = 1.0

                case.metadata["convergence_trace"].append(max_se_diff)
                self._log_event(
                    ConvergenceCheckEvent(
                        case_id=case.id,
                        trial_index=trial_idx,
                        max_se_diff=max_se_diff,
                        se_map=se_map,
                        threshold=self.config.se_threshold,
                    )
                )

                if trials_completed % 10 == 0:
                    print(
                        f"      {Style.DIM}[Progress] Converged: {converged_count}/{len(fqns)} | Max SE: {max_se_diff:.4f}{Style.RESET_ALL}"
                    )

                if mode == "adaptive" and trials_completed >= min_n:
                    if self._check_convergence(
                        fqns,
                        trials_in,
                        success_in,
                        trials_out,
                        success_out,
                        self.config.se_threshold,
                    ):
                        print(
                            f"      {Fore.GREEN}✔ Convergence reached (Trial {trial_idx+1}). Stopping.{Style.RESET_ALL}"
                        )
                        stop_signal = True

        tasks = [run_single_trial(i) for i in range(max_n)]
        await asyncio.gather(*tasks)

        print(f"  {Fore.CYAN}➤ Impact Scores (Sorted by impact):{Style.RESET_ALL}")

        sorted_fqns = sorted(
            fqns,
            key=lambda x: (
                success_in[x] / trials_in[x] - success_out[x] / trials_out[x]
            )
            if (trials_in[x] > 0 and trials_out[x] > 0)
            else 0,
            reverse=True,
        )

        for f in sorted_fqns:
            n_in, n_out = trials_in[f], trials_out[f]
            p_in = success_in[f] / n_in if n_in > 0 else 0.0
            p_out = success_out[f] / n_out if n_out > 0 else 0.0
            delta_p = p_in - p_out
            se_in = math.sqrt(p_in * (1 - p_in) / n_in) if n_in > 0 else 0.0

            ctx = c_map[f]
            ctx.metadata = RetrievalResultMetadata(
                delta_p=round(delta_p, 2),
                p_in=round(p_in, 2),
                p_out=round(p_out, 2),
                n_in=n_in,
                n_out=n_out,
                se_in=round(se_in, 3),
            )

            color = (
                Fore.GREEN
                if delta_p > 0.1
                else (Fore.RED if delta_p < -0.1 else Fore.WHITE)
            )
            print(
                f"    [{delta_p:+.2f}] {color}{f:<60}{Style.RESET_ALL} (SE: {se_in:.2f})"
            )

            if ctx.context_type == "random_noise" and delta_p > 0.1:
                print(
                    f"      {Fore.RED}⚠ Pooling Violation: Random doc found relevant!{Style.RESET_ALL}"
                )
                self._log_event(
                    PoolingViolationEvent(case_id=case.id, fqn=f, delta_p=delta_p)
                )

        if candidates:
            combined_text = "\n\n".join(
                [
                    f"[START_DOCUMENT: {c.fqn}]\n{c.text}\n[END_DOCUMENT]"
                    for c in candidates
                ]
            )
            final_ans, _ = await self._generate_answer_with_retry(case, combined_text)
            case.is_sufficient_set = False
            if final_ans:
                try:
                    if case.source == "api_understanding":
                        case.is_sufficient_set, _ = (
                            await self._validate_api_understanding(case, final_ans)
                        )
                    elif case.source == "fix_errors":
                        case.is_sufficient_set, _ = await self._validate_fix_errors(
                            case, final_ans
                        )
                    elif case.source == "multiple_choice":
                        case.is_sufficient_set, _ = (
                            await self._validate_multiple_choice(case, final_ans)
                        )
                except Exception:
                    pass

            suff_color = Fore.GREEN if case.is_sufficient_set else Fore.RED
            print(
                f"  {Fore.CYAN}➤ Total Pool Sufficiency: {suff_color}{case.is_sufficient_set}{Style.RESET_ALL}"
            )

        return case

    def _check_convergence(
        self, fqns, trials_in, success_in, trials_out, success_out, threshold
    ):
        """
        Returns True if the Standard Error of Delta P for ALL documents is below the threshold.
        Uses an adjusted SE of 1/N for p=0 or p=1 to prevent premature stopping.
        """
        max_se = 0.0
        for f in fqns:
            if trials_in[f] == 0 or trials_out[f] == 0:
                return False
            p_in = success_in[f] / trials_in[f]
            p_out = success_out[f] / trials_out[f]
            se_in = (
                math.sqrt(p_in * (1 - p_in) / trials_in[f])
                if (0 < p_in < 1)
                else (1.0 / trials_in[f])
            )
            se_out = (
                math.sqrt(p_out * (1 - p_out) / trials_out[f])
                if (0 < p_out < 1)
                else (1.0 / trials_out[f])
            )
            se_diff = math.sqrt(se_in**2 + se_out**2)
            max_se = max(max_se, se_diff)
        return max_se < threshold

    async def _generate_answer_with_retry(
        self, case: RetrievalCase, context: str
    ) -> Tuple[Optional[GeneratedAnswer], str]:
        """
        Calls the LLM to generate an answer for the given case and context.
        Enforces structured output JSON matching the benchmark type.
        """
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

        # TODO: Throw a warning if prompt length exceeds model limits but do not truncate.
        prompt = f"""You are an expert developer.
Context:
{context}

Task: {question_text}

Instructions:
1. Answer the question using ONLY the provided context. Do NOT use any preconceived knowledge.
2. If the context is insufficient to answer confidently, populate the `refusal_reason` field with an explanation and provide dummy values for other required fields.
3. You MUST output a valid JSON object matching the schema below.

Target Schema:
{schema_json}
"""
        key_val, key_id = await self.api_key_manager.get_next_key_with_id(
            KeyType.GEMINI_API
        )
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
                    "response_schema": target_schema,
                },
            )
            await self.api_key_manager.report_result(KeyType.GEMINI_API, key_id, True)
            return GeneratedAnswer(raw_output=response.text), prompt

        except Exception as e:
            error_msg = str(e)
            await self.api_key_manager.report_result(
                KeyType.GEMINI_API, key_id, False, error_message=error_msg
            )
            return None, prompt

    async def _validate_api_understanding(
        self, case: RetrievalCase, answer: GeneratedAnswer
    ) -> Tuple[bool, Optional[str]]:
        """Validates an API understanding answer using StringMatchRunner."""
        gt = case.ground_truth
        if not gt.get("answers"):
            return False, "No ground truth answers"
        bcase = ApiUnderstandingBenchmarkCase(
            id=case.id,
            question=case.query,
            category=case.metadata.get("category", "unknown"),
            rationale="N/A",
            template=AnswerTemplate(gt.get("template", "identifier")),
            answers=[StringMatchAnswer(**a) for a in gt.get("answers", [])],
            file=Path("unknown"),
            benchmark_type=BenchmarkType.API_UNDERSTANDING,
        )
        runner = ApiUnderstandingRunner()
        try:
            answer.output = await self.sanitizer.sanitize(
                answer.raw_output, ApiUnderstandingAnswerOutput
            )
            if getattr(answer.output, "refusal_reason", None):
                return False, f"Model Refusal: {answer.output.refusal_reason}"
            result, _, _, _ = await runner.run_benchmark(bcase, answer)
            return result == BenchmarkResultType.PASS, None
        except Exception as e:
            return False, str(e)

    async def _validate_fix_errors(
        self, case: RetrievalCase, answer: GeneratedAnswer
    ) -> Tuple[bool, Optional[str]]:
        """Validates a fix_error answer by running pytest against the generated code."""
        gt = case.ground_truth

        def to_path(p):
            return Path(p) if p else None

        bcase = FixErrorBenchmarkCase(
            id=case.id,
            name=gt.get("name", "unknown"),
            description=gt.get("description", "unknown"),
            test_file=to_path(gt.get("test_file")),
            unfixed_file=to_path(gt.get("unfixed_file")),
            fixed_file=to_path(gt.get("fixed_file")),
            requirements=gt.get("requirements"),
            error_output=gt.get("error_output"),
            benchmark_type=BenchmarkType.FIX_ERROR,
        )
        runner = PytestBenchmarkRunner()
        try:
            answer.output = await self.sanitizer.sanitize(
                answer.raw_output, FixErrorAnswerOutput
            )
            if getattr(answer.output, "refusal_reason", None):
                return False, f"Model Refusal: {answer.output.refusal_reason}"
            result, logs, _, _ = await runner.run_benchmark(bcase, answer)
            error_msg = (
                None
                if result == BenchmarkResultType.PASS
                else f"Runner Result: {result}, Logs: {logs}"
            )
            return result == BenchmarkResultType.PASS, error_msg
        except Exception as e:
            return False, str(e)

    async def _validate_multiple_choice(
        self, case: RetrievalCase, answer: GeneratedAnswer
    ) -> Tuple[bool, Optional[str]]:
        """Validates a multiple choice answer."""
        gt = case.ground_truth
        bcase = MultipleChoiceBenchmarkCase(
            id=case.id,
            question=case.query,
            options=gt.get("options", {}),
            correct_answer=gt.get("correct_answer"),
            explanation=gt.get("explanation"),
            benchmark_type=BenchmarkType.MULTIPLE_CHOICE,
        )
        runner = MultipleChoiceRunner()
        try:
            answer.output = await self.sanitizer.sanitize(
                answer.raw_output, MultipleChoiceAnswerOutput
            )
            if getattr(answer.output, "refusal_reason", None):
                return False, f"Model Refusal: {answer.output.refusal_reason}"
            result, _, _, _ = await runner.run_benchmark(bcase, answer)
            error_msg = (
                None
                if result == BenchmarkResultType.PASS
                else f"Wrong Answer. Expected {gt.get('correct_answer')}, Got {answer.output.answer}"
            )
            return result == BenchmarkResultType.PASS, error_msg
        except Exception as e:
            return False, str(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieval Data Validator")
    parser.add_argument(
        "--input", default="retrieval_dataset.yaml", help="Input dataset path"
    )
    parser.add_argument(
        "--mode",
        default="adaptive",
        choices=["fixed", "adaptive"],
        help="Sampling mode",
    )
    parser.add_argument(
        "--max-cases", type=int, default=None, help="Limit number of cases"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing output file if present.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output file if present.",
    )

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Fixed run directory for resume capability testing, or timestamped for new runs?
    # To support "retry from crash", we need a stable path or user provided path.
    # For this implementation, we assume we are running in a specific experiment context or we check the default output.
    # But the output path is inside a timestamped dir.
    # Let's verify if 'retrieval_dataset_verified.yaml' exists in current dir or specific dir.
    # Actually, the previous code generated a NEW timestamped dir every time. This makes resume hard unless we pass the dir.
    # Let's check if the user provided an output path, otherwise generate one.

    # IMPROVEMENT: To support resume, we should look for the latest run or a specific output.
    # For now, let's keep the timestamp behavior but check if the user *intended* to resume a specific run.
    # But the requirement is "detect if a crashed repo state exists".
    # We'll check for 'retrieval_dataset_verified.yaml' in the *current* directory as a convention for "active work",
    # or allow the user to specify the output directory.

    # Let's stick to the timestamp dir for new runs, but if we want to resume, we probably need to point to it.
    # However, the user asked to "detect if a crashed repo state exists".
    # We can look for the most recent run directory.

    latest_run = None
    runs = sorted(Path("retrieval_evals").glob("run_*"))
    if runs:
        latest_run = runs[-1]

    if latest_run and (latest_run / "retrieval_dataset_verified.yaml").exists():
        if not args.resume and not args.overwrite:
            print(f"{Fore.YELLOW}Found existing run at {latest_run}.{Style.RESET_ALL}")
            response = input("Do you want to RESUME this run? [y/N/new]: ").lower()
            if response == "y":
                args.resume = True
                run_dir = latest_run
            elif response == "new":
                args.overwrite = True
            else:
                # Default to new run
                pass

    if args.resume and latest_run:
        run_dir = latest_run
        print(f"{Fore.GREEN}Resuming run from: {run_dir}{Style.RESET_ALL}")
    else:
        run_dir = Path(f"retrieval_evals/run_{timestamp}")
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"{Fore.CYAN}Starting NEW Validation Run in: {run_dir}{Style.RESET_ALL}")

    output_path = run_dir / "retrieval_dataset_verified.yaml"
    log_file = run_dir / "validation_events.yaml"

    key_val = asyncio.run(API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API))
    if not key_val:
        print("No API key available.")
        exit(1)

    targets_path = "benchmarks.generator.benchmark_generator/data/ranked_targets.yaml"

    print(f"{Fore.CYAN}Initializing Retrievers...{Style.RESET_ALL}")
    with open(targets_path, "r") as f:
        raw_targets = yaml.safe_load(f)
        if not isinstance(raw_targets, list):
            raw_targets = raw_targets.get("targets", [])
        targets = [
            RankedTarget(id=t["id"], name=t["name"], docstring=t.get("docstring", ""))
            for t in raw_targets
            if t.get("id")
        ]

    gold_miner = GoldMinerRetriever()
    asyncio.run(gold_miner.index(targets))
    random_retriever = RandomRetriever()
    asyncio.run(random_retriever.index(targets))
    embedding_retriever = EmbeddingRetriever(api_key=key_val)
    asyncio.run(embedding_retriever.index(targets))

    config = ValidatorConfig(log_file=str(log_file))

    validator = DataValidator(
        args.input,
        str(output_path),
        retrievers=[gold_miner, embedding_retriever, random_retriever],
        config=config,
    )
    asyncio.run(validator.validate_dataset(max_cases=args.max_cases, mode=args.mode))

    print(f"\n{Fore.GREEN}Generating Analysis Report...{Style.RESET_ALL}")
    try:
        from tools.retrieval_dataset_generation.generate_report import generate_report

        report_path = run_dir / "retrieval_analysis_report.md"
        generate_report(str(output_path), str(report_path), str(log_file))
    except Exception as e:
        print(f"{Fore.RED}Failed to generate report: {e}{Style.RESET_ALL}")
