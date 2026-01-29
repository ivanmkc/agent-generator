"""
CLI tool to generate a comprehensive Markdown report for a benchmark run.

This script analyzes the `results.json` and `trace.yaml` of a specific run,
performs forensic analysis on failures, and uses an LLM (via Map-Reduce) to
synthesize an executive summary and actionable recommendations.
"""

import asyncio
import os
import sys
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
import pydantic
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Add project root to sys.path to allow imports from benchmarks when running directly
# tools/cli/generate_benchmark_report.py -> tools/cli -> tools -> root
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from google.genai import Client, types
from core.api_key_manager import API_KEY_MANAGER, KeyType
from benchmarks.data_models import (
    BenchmarkRunResult,
    TraceEventType,
    ForensicInsight,
    CaseSummary,
    GeneratorForensicSummary,
    ForensicData,
)
from benchmarks.analysis import (
    process_results,
    get_token_usage_stats,
    get_tool_success_stats,
    format_as_markdown,
    Bcolors,
)
from tools.analysis.run_metrics import analyze_benchmark_run
from tools.analysis.generate_architecture_docs import DOC_MANAGER
from tools.analysis.summarize_cases import CASE_DOC_MANAGER
from benchmarks.benchmark_candidates import CANDIDATE_GENERATORS
from core.config import MOST_POWERFUL_MODEL, BENCHMARK_RUNS_DIR

# Configure logging to suppress noisy libraries
import logging

logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Pydantic Models for Structured Report ---


class GeneratorAnalysisSection(BaseModel):
    generator_name: str = Field(..., description="Name of the generator.")
    performance_summary: str = Field(
        ..., description="Summary of performance (Stability, Retry patterns, etc.)."
    )
    docs_context_analysis: str = Field(
        ..., description="Analysis of Docs/Context injection effectiveness."
    )
    tool_usage_analysis: str = Field(
        ..., description="Analysis of tool usage effectiveness and errors."
    )
    general_error_analysis: str = Field(
        ...,
        description="Analysis of general errors (logic, syntax, etc.) with embedded examples.",
    )


class HighLevelInsights(BaseModel):
    executive_summary: str = Field(
        ...,
        description="High-level overview of the session, organized by Generator and Suite.",
    )
    cross_generator_comparison: str = Field(
        ..., description="Comparison on Quality, Efficiency, Latency, and Stability."
    )
    recommendations: List[str] = Field(
        ..., description="List of actionable recommendations."
    )


# --- Prompts ---

FORENSIC_PROMPT = """You are a rigorous Forensic Software Analyst auditing a SINGLE ATTEMPT of an autonomous agent.

Benchmark: "{benchmark_name}"
Attempt Error: "{error_message}"

=== TRACE LOGS (Snippet) ===
{trace_json}
=================================

Your Goal: Determine the *exact* moment and reason this attempt failed. Select the BEST matching category.

Categories:
- **Retrieval: Zero Results (Bad Query):** Agent called tools with invalid args or keywords that yielded 0 results, and failed to fix it.
- **Retrieval: Shallow (Missing Follow-up):** Agent retrieved some context but it was insufficient, and it failed to dig deeper.
- **Reasoning: Ignored Context (Hallucination):** The answer was in the tool output, but the agent contradicted it.
- **Reasoning: Fabrication (No Context):** Agent had zero context and guessed.
- **Output: Schema Violation:** Malformed JSON or missing fields.
- **Output: Logic Error:** Valid code/output but failed the test assertion.
- **Execution: Tool Misuse:** Syntax error in tool call or loop exit before completion.
- **Infrastructure:** 429, 500, Timeout.

INSTRUCTIONS:
1. Audit Tool Calls (Inputs/Outputs).
2. Audit Reasoning (Thoughts vs Data).
3. Audit Output (Schema/Logic).

Output a structured JSON analysis.
"""

CASE_REDUCTION_PROMPT = """You are a Lead Investigator synthesizing multiple failure attempts for a single benchmark case.

Benchmark: "{benchmark_name}"

=== ATTEMPT INSIGHTS ===
{insights_json}
========================

Your Goal: Identify the *persistent* root cause and the agent's behavioral trajectory.

1. **Pattern:** Is the agent repeating the same mistake, or trying new (bad) strategies?
2. **Progression:** Is it getting closer to the solution or drifting?
3. **Root Cause:** What is the fundamental blocker? (e.g., "Knowledge Gap", "Reasoning Loop", "Tool Failure").

Output a structured summary.
"""

GENERATOR_FORENSIC_PROMPT = """You are a Chief AI Architect reviewing a forensic report for an AI Agent Generator.

Generator Name: "{generator_name}"

=== FAILED CASE SUMMARIES ===
{case_summaries_json}
=============================

Your Goal: Synthesize these individual case failures into a high-level generator diagnosis.

1. **Identify Systemic Issues:** specific patterns that appear across multiple cases (e.g. "The agent consistently ignores empty search results").
2. **Highlight Anti-Patterns:** Dangerous or wasteful behaviors (e.g. "Hallucinating APIs when search fails").
3. **Recommend Fixes:** Architectural changes to the agent logic or prompt engineering.

Output a structured summary.
"""

# ---------------------------------------------


class LogAnalyzer:
    """
    Analyzes benchmark logs using Gemini to provide insights and summaries.
    Uses pandas to group results by Generator -> Suite -> Case -> Attempt.
    """

    def __init__(self, model_name: str):
        if not model_name:
            raise ValueError("model_name is required for LogAnalyzer.")
        self.model_name = model_name
        self.meta_stats = {
            "start_time": 0,
            "llm_calls": 0,
            "total_tokens": 0,
            "errors": 0,
        }

    async def _get_client(self):
        """Initializes the Gemini client with a rotated API key."""
        api_key = await API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)
        if not api_key:
            raise ValueError("No API key available for LogAnalyzer.")
        return Client(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=20),
        retry=retry_if_exception_type(
            Exception
        ),  # The SDK usually raises generic Exception or specific APIError
    )
    async def _generate_content(self, prompt: str, schema: Any = None) -> Any:
        """Generates content using the Gemini API, optionally enforcing a schema."""
        self.meta_stats["llm_calls"] += 1
        client = await self._get_client()

        config = {}
        if schema:
            config = types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=schema
            )

        response = await client.aio.models.generate_content(
            model=self.model_name,
            contents=[types.Content(parts=[types.Part(text=prompt)])],
            config=config,
        )

        # Track usage if available
        if response.usage_metadata:
            self.meta_stats["total_tokens"] += response.usage_metadata.total_token_count

        if schema:
            # If schema is used, parse the JSON response
            try:
                obj = schema.model_validate_json(response.text)
                # print(f"[DEBUG] Parsed object type: {type(obj)}")
                return obj
            except Exception as e:
                print(f"Error parsing JSON response: {e}")
                print(f"Raw text was: {response.text}")
                self.meta_stats["errors"] += 1
                raise e

        return response.text

    def _get_archetype_key_from_meta(self, gen_meta: Dict[str, Any]) -> str:
        """Reconstructs the archetype key from generator metadata."""
        image_name = gen_meta.get("image_name")
        name = gen_meta.get("name", "")

        if image_name:
            return f"GeminiCliPodman: {image_name}"

        if "(" in name:
            return name.split("(")[0]
        return name

    async def _load_static_context(self, run_dir: Path) -> str:
        """
        Loads runtime params and generates/retrieves static architecture docs.
        """
        metadata_path = run_dir / "run_metadata.json"

        if not metadata_path.exists():
            return "No run metadata found."

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            return f"Error loading run_metadata.json: {e}"

        context_parts = []
        generators_meta = meta.get("generators", [])

        candidate_generators = CANDIDATE_GENERATORS
        candidate_map = {g.name: g for g in candidate_generators}

        for gen_meta in generators_meta:
            name = gen_meta.get("name", "Unknown")
            model = gen_meta.get("model_name", "Unknown")
            key = self._get_archetype_key_from_meta(gen_meta)

            context_parts.append(f"### {name}")

            candidate_obj = None

            if "GeminiCliPodman" in key and ": " in key:
                try:
                    image_search = key.split(": ", 1)[1].strip()
                    for c_name, c_obj in candidate_map.items():
                        if (
                            hasattr(c_obj, "image_name")
                            and c_obj.image_name == image_search
                        ):
                            candidate_obj = c_obj
                            break
                except Exception:
                    pass

            if not candidate_obj:
                for c_name, c_obj in candidate_map.items():
                    if key in c_name:
                        candidate_obj = c_obj
                        break

            context_parts.append(f"- **Model:** `{model}`")
            if not candidate_obj:
                context_parts.append(
                    f"- **Archetype Key:** `{key}` (Code definition not found in current runtime)"
                )

            desc = await DOC_MANAGER.get_description(
                key, candidate_obj, self.model_name
            )
            context_parts.append(desc)

            context_parts.append("\n")

        return "\n".join(context_parts)

    def _calculate_quantitative_stats(
        self,
        results_df: pd.DataFrame,
        results_list: List[BenchmarkRunResult],
    ) -> str:
        """Calculates quantitative statistics from the results DataFrame."""
        if results_df.empty:
            return "No quantitative results available."

        stats_lines = ["## 4. Quantitative Analysis\n"]

        stats_lines.append("#### Metric Definitions & Methodology\n")
        stats_lines.append("| Metric | Definition | Calculation |")
        stats_lines.append("| :--- | :--- | :--- |")
        stats_lines.append(
            "| **Overall Pass Rate** | Percentage of benchmark cases where the generator produced a correct, passing answer (Score = 1). | `(Passed Cases / Total Cases) * 100` |")
        stats_lines.append(
            "| **Avg Latency** | Average execution time for *passing* cases only. | `Mean(Duration)` of successful runs. |"
        )
        stats_lines.append(
            "| **Est. Cost** | Estimated total cost based on token usage across all attempts (success + fail). | `(Total Tokens / 1,000,000) * $0.10` (Blended Input/Output Rate for Gemini 2.5 Flash). |"
        )
        stats_lines.append("\n")

        token_df = get_token_usage_stats(results_list)
        all_suites = sorted(results_df["suite"].unique())

        leaderboard_data = []
        for gen_name, group in results_df.groupby("answer_generator"):
            total_cases = len(group)
            passed_cases = group["result"].sum()
            pass_rate = (passed_cases / total_cases) * 100 if total_cases > 0 else 0

            success_latency = group[group["result"] == 1]["latency"].mean()
            if pd.isna(success_latency):
                success_latency = 0.0

            total_tokens = 0
            if not token_df.empty:
                gen_tokens = token_df[token_df["Generator"] == gen_name]
                total_tokens = gen_tokens["Total Tokens"].sum()

            cost = (total_tokens / 1_000_000) * 0.10

            entry = {
                "Generator": gen_name,
                "Overall Pass Rate": f"{pass_rate:.1f}%",
                "Avg Latency": f"{success_latency:.2f}s",
                "Est. Cost": f"${cost:.3f}",
            }

            for suite in all_suites:
                suite_group = group[group["suite"] == suite]
                if not suite_group.empty:
                    s_passed = suite_group["result"].sum()
                    s_total = len(suite_group)
                    s_rate = (s_passed / s_total) * 100
                    entry[suite] = f"{s_rate:.1f}%"
                else:
                    entry[suite] = "-"

            leaderboard_data.append(entry)

        leaderboard_df = pd.DataFrame(leaderboard_data).sort_values(
            "Overall Pass Rate", ascending=False
        )
        stats_lines.append(format_as_markdown(leaderboard_df))
        stats_lines.append("\n")

        # 3. Tool Success & Impact
        stats_lines.append("#### Tool Success & Impact\n")
        stats_lines.append(
            "Methodology: 'Case Pass Rate' is the percentage of benchmark cases where the tool was used and the case passed. 'Lift' compares this to the overall pass rate.\n"
        )

        try:
            tool_df = get_tool_success_stats(results_list)
            if not tool_df.empty:
                # Format percentages
                tool_df["success_rate"] = (tool_df["success_rate"] * 100).map(
                    "{:.1f}%".format
                )
                tool_df["lift"] = (tool_df["lift"] * 100).map("{:+.1f}%".format)
                # Rename columns for display
                tool_df = tool_df.rename(
                    columns={
                        "tool": "Tool",
                        "times_used": "Cases Used",
                        "successes": "Successes",
                        "success_rate": "Case Pass Rate",
                        "lift": "Lift",
                    }
                )
                # Select relevant columns
                display_cols = ["Tool", "Cases Used", "Case Pass Rate", "Lift"]
                stats_lines.append(format_as_markdown(tool_df[display_cols]))
            else:
                stats_lines.append("No tool usage detected.")
        except Exception as e:
            stats_lines.append(f"Error calculating tool stats: {e}")
        stats_lines.append("\n")

        return "\n".join(stats_lines)

    async def _format_generator_logs(
        self,
        generator_name: str,
        results_list: List[BenchmarkRunResult],
    ) -> str:
        """
        Formats the execution logs for a specific generator into a structured text block for the LLM.
        """
        MAX_TOTAL_CHARS = 1_000_000
        MAX_ERROR_CHARS = 10_000

        lines = [f"GENERATOR: {generator_name}"]
        current_chars = len(lines[0])

        df = pd.DataFrame([r.model_dump() for r in results_list])

        if df.empty:
            return f"No results found for generator: {generator_name}"

        if "suite" in df.columns:
            df["suite"] = df["suite"].apply(lambda x: Path(x).parent.name)
        else:
            df["suite"] = "unknown_suite"

        for suite_name, suite_group in df.groupby("suite"):
            if current_chars > MAX_TOTAL_CHARS:
                lines.append(
                    f"\n[TRUNCATED REMAINING LOGS DUE TO SIZE LIMIT ({MAX_TOTAL_CHARS} chars)]"
                )
                break

            total = len(suite_group)
            passed = suite_group["result"].sum()
            rate = (passed / total) * 100 if total > 0 else 0

            suite_header = (
                f"\nSUITE: {suite_name} (Pass Rate: {rate:.1f}% - {passed}/{total})"
            )
            lines.append(suite_header)
            current_chars += len(suite_header)

            for _, row in suite_group.iterrows():
                if current_chars > MAX_TOTAL_CHARS:
                    break

                case_name = row["benchmark_name"]
                result = "PASS" if row["result"] == 1 else "FAIL"
                icon = "✅" if row["result"] == 1 else "❌"

                # Fetch one-liner
                prompt = row.get("prompt", "")
                one_liner = await CASE_DOC_MANAGER.get_one_liner(
                    case_name, prompt, self.model_name
                )

                # Sanitize one-liner
                if one_liner:
                    one_liner = one_liner.replace("\n", " ").strip()
                    if (
                        "compliance with the License" in one_liner
                        or "apache.org/licenses" in one_liner
                    ):
                        one_liner = "Check source for details."

                case_line = f'\n  CASE: {case_name} -- "{one_liner}" -> {icon} {result}'
                lines.append(case_line)
                current_chars += len(case_line)

                if row["result"] == 0:
                    lines.append("\n> **Expected vs Actual**")

                    gt = f"> **Ground Truth:**\n> {row['ground_truth']}"
                    # Indent the answer for the blockquote
                    answer_text = str(row["answer"])[:1000].replace("\n", "\n> ")
                    ans = f"> **Model Answer:**\n> {answer_text}..."

                    lines.append(gt)
                    lines.append(">\n" + ans)
                    current_chars += len(gt) + len(ans)

                if row["validation_error"]:
                    val_err = f"    Validation Error: {row['validation_error']}"
                    lines.append(val_err)
                    current_chars += len(val_err)

                attempts = row.get("generation_attempts", [])
                if attempts:
                    lines.append("    Attempts:")
                    for att in attempts:
                        if isinstance(att, dict):
                            a_num = att.get("attempt_number")
                            a_status = att.get("status")
                            a_dur = att.get("duration", 0)
                            a_err = att.get("error_message")
                        else:
                            a_num = att.attempt_number
                            a_status = att.status
                            a_dur = att.duration
                            a_err = att.error_message

                        att_line = (
                            f"      Attempt {a_num}: {a_status.upper()} ({a_dur:.2f}s)"
                        )
                        lines.append(att_line)
                        current_chars += len(att_line)

                        # Add tool usage summary
                        logs = (
                            att.get("trace_logs", [])
                            if isinstance(att, dict)
                            else (att.trace_logs or [])
                        )

                        if logs:
                            tools_used = []
                            for log in logs:
                                t_type = (
                                    log.get("type")
                                    if isinstance(log, dict)
                                    else log.type
                                )
                                t_name = (
                                    log.get("tool_name")
                                    if isinstance(log, dict)
                                    else log.tool_name
                                )
                                if str(t_type) == "tool_use" and t_name:
                                    tools_used.append(t_name)

                            if tools_used:
                                tool_line = (
                                    f"        Tools Used: {', '.join(tools_used)}"
                                )
                                lines.append(tool_line)
                                current_chars += len(tool_line)

                        if a_err:
                            # Filter out noisy [DEBUG] lines from logs
                            filtered_err_lines = [
                                l for l in a_err.splitlines() if "[DEBUG]" not in l
                            ]
                            a_err = "\n".join(filtered_err_lines)

                            if len(a_err) > MAX_ERROR_CHARS:
                                a_err = (
                                    a_err[:MAX_ERROR_CHARS]
                                    + f" ... [TRUNCATED {len(a_err) - MAX_ERROR_CHARS} chars]"
                                )

                            err_line = f"        Error Output:\n{a_err}"
                            lines.append(err_line)
                            current_chars += len(err_line)

        return "\n".join(lines)

    async def _analyze_generator(
        self,
        generator_name: str,
        log_text: str,
        tool_stats_text: str = "",
    ) -> GeneratorAnalysisSection:
        """
        Analyzes the logs for a single generator and returns a structured object.
        """

        tool_context = (
            f"\nComputed Tool Usage Stats for this Generator:\n{tool_stats_text}\n"
            if tool_stats_text
            else ""
        )

        prompt = f"""
        Analyze the logs for generator: {generator_name}
        {tool_context}
        Focus on:
        1. Performance summary (Stability, patterns).
        2. Effectiveness of context/docs provided.
        3. Tool usage (effective vs errors). Use the 'Computed Tool Usage Stats' above as the authoritative reference for quantitative counts.
        4. General error types.
        
        Logs:
        {log_text}
        """

        try:
            return await self._generate_content(prompt, schema=GeneratorAnalysisSection)
        except Exception as e:
            print(f"Error analyzing generator {generator_name}: {e}")
            # Return a placeholder object on failure to avoid crashing the pipeline
            return GeneratorAnalysisSection(
                generator_name=generator_name,
                performance_summary="Analysis Failed.",
                docs_context_analysis="Analysis Failed.",
                tool_usage_analysis="Analysis Failed.",
                general_error_analysis=f"Analysis Failed: {str(e)}",
            )

    async def _generate_high_level_insights(
        self,
        generator_summaries: str,
        quantitative_context: str,
    ) -> HighLevelInsights:
        """
        Generates the Executive Summary, Cross-Generator Comparison, and Recommendations based on
        the aggregated quantitative stats and per-generator summaries.
        """

        prompt = f"""
        You are a Lead AI Engineer creating a final Benchmark Execution Report.
        
        Based on the quantitative data and generator summaries provided below, generate the high-level insights for the report. 
        
        **Quantitative Stats:**
        {quantitative_context}

        **Generator Summaries:**
        {generator_summaries}
        
        Produce a structured output containing:
        1. Executive Summary
        2. Cross-Generator Comparison
        3. Recommendations
        """

        try:
            return await self._generate_content(prompt, schema=HighLevelInsights)
        except Exception as e:
            print(f"Error generating high-level insights: {e}")
            return HighLevelInsights(
                executive_summary="Failed to generate.",
                cross_generator_comparison="Failed to generate.",
                recommendations=["Failed to generate."],
            )

    async def _analyze_attempt(
        self,
        case_name: str,
        attempt_idx: int,
        attempt_analysis: Any,
    ) -> Optional[ForensicInsight]:
        """Uses LLM to perform deep forensic analysis on a single attempt."""

        # Serialize trace (truncate if huge)
        trace_events = []
        for evt in attempt_analysis.trace_logs:
            trace_events.append(
                {
                    "author": evt.get("author"),
                    "tool": evt.get("tool_name"),
                    "input": str(evt.get("tool_input"))[:200],
                    "output": str(evt.get("tool_output"))[:200],
                    "thought": str(evt.get("content"))[:300],
                }
            )

        trace_str = json.dumps(trace_events, indent=2)
        if len(trace_str) > 50000:
            trace_str = trace_str[:25000] + "\n...[TRUNCATED]...\n" + trace_str[-25000:]

        prompt = FORENSIC_PROMPT.format(
            benchmark_name=case_name,
            error_message=attempt_analysis.error_message,
            trace_json=trace_str,
        )

        try:
            return await self._generate_content(prompt, schema=ForensicInsight)
        except Exception as e:
            print(f"LLM Analysis failed for {case_name} (Attempt {attempt_idx}): {e}")
            return None

    async def _reduce_case_insights(
        self,
        case_name: str,
        attempt_insights: List[ForensicInsight],
    ) -> Optional[CaseSummary]:
        """Reduces multiple attempt insights into a single case summary (Level 2)."""
        if not attempt_insights:
            return None

        insights_json = json.dumps([i.model_dump() for i in attempt_insights], indent=2)

        prompt = CASE_REDUCTION_PROMPT.format(
            benchmark_name=case_name, insights_json=insights_json
        )

        try:
            return await self._generate_content(prompt, schema=CaseSummary)
        except Exception as e:
            print(f"Case Reduction failed for {case_name}: {e}")
            return None

    async def _summarize_generator_forensics(
        self,
        generator_name: str,
        case_summaries: List[CaseSummary],
    ) -> GeneratorForensicSummary:
        """Synthesizes individual case summaries into a generator-level diagnostic."""

        # Serialize summaries
        summaries_json = json.dumps([c.model_dump() for c in case_summaries], indent=2)

        prompt = GENERATOR_FORENSIC_PROMPT.format(
            generator_name=generator_name, case_summaries_json=summaries_json
        )

        try:
            return await self._generate_content(prompt, schema=GeneratorForensicSummary)
        except Exception as e:
            print(f"Generator forensic summary failed for {generator_name}: {e}")
            return GeneratorForensicSummary(
                common_failure_patterns="Failed to analyze.",
                critical_anti_patterns="Failed to analyze.",
                strategic_recommendations=["Failed to analyze."],
            )

    def _get_suite_context(self, results_df: pd.DataFrame) -> str:
        """Generates a table of benchmark suites and their objectives."""
        if results_df.empty:
            return ""

        suites = results_df["suite"].unique()

        known_suites = {
            "api_understanding": "Tests the model's ability to recall correct import paths and class signatures without hallucination. Requires strict adherence to the ADK library structure.",
            "fix_errors": "Tests the model's ability to debug and fix broken code snippets using the ADK. Measures reasoning and self-correction.",
            "multiple_choice": "Tests general reasoning or specific knowledge selection from provided options.",
        }

        suite_data = []
        for s in suites:
            desc = "Custom benchmark suite."
            if "api_understanding" in s:
                desc = known_suites["api_understanding"]
            elif "fix_errors" in s:
                desc = known_suites["fix_errors"]
            elif "_mc" in s:
                desc = known_suites["multiple_choice"]

            suite_data.append({"Suite": f"`{s}`", "Objective": desc})

        suite_df = pd.DataFrame(suite_data)

        return (
            "\n\n## Benchmark Suites Overview\n" + format_as_markdown(suite_df) + "\n"
        )

    def _assemble_report(
        self,
        insights: HighLevelInsights,
        generator_analyses: List[GeneratorAnalysisSection],
        static_context: str,
        quantitative_context: str,
        suite_context: str,
        forensic_context: str = "",
    ) -> str:
        """
        Programmatically assembles the final Markdown report from all components.
        """
        md = ["# 📊 Benchmark Run Analysis\n"]

        # 1. Generator Internals
        md.append("## 1. Generator Internals & Configuration")
        md.append(static_context)
        md.append("\n")

        # 2. Executive Summary
        md.append("## 2. Executive Summary")
        md.append(insights.executive_summary)
        md.append("\n")

        # 3. Benchmark Suites
        md.append("## 3. Benchmark Suites Overview")
        # suite_context already has the table
        md.append(suite_context.replace("## Benchmark Suites Overview", "").strip())
        md.append("\n")

        # 4. Quantitative Analysis
        md.append(quantitative_context)
        md.append("\n")

        # 5. Generator Analysis
        md.append("## 5. Generator Analysis")
        for gen in generator_analyses:
            md.append(f"### {gen.generator_name}")
            md.append(f"**Performance:** {gen.performance_summary}\n")
            md.append(f"#### Docs/Context Injection\n{gen.docs_context_analysis}\n")
            md.append(f"#### Tool Usage\n{gen.tool_usage_analysis}\n")
            md.append(f"#### General Errors\n{gen.general_error_analysis}\n")
            md.append("---\n")

        # 6. Cross-Generator Comparison
        md.append("## 6. Cross-Generator Comparison")
        md.append(insights.cross_generator_comparison)
        md.append("\n")

        # 7. Recommendations
        md.append("## 7. Recommendations")
        for rec in insights.recommendations:
            md.append(f"*   {rec}")
        md.append("\n")

        # 8. Forensic Analysis
        if forensic_context:
            md.append("## 8. Forensic Analysis (Deep Dive)")

            # Post-process forensic_context to remove redundant copyright headers
            # that might be interpreted as H1 headers by the viewer.
            cleaned_forensic = []
            for line in forensic_context.splitlines():
                lower_line = line.lower()
                if (
                    lower_line.startswith("# copyright")
                    or lower_line.startswith("# licensed under")
                    or lower_line.strip() == "#"
                    or "compliance with the license" in lower_line
                    or "apache.org/licenses" in lower_line
                ):
                    continue
                cleaned_forensic.append(line)

            md.append("\n".join(cleaned_forensic))
            md.append("\n")

        # 9. Report Metadata
        import time

        duration = time.time() - self.meta_stats["start_time"]
        md.append("## 9. Report Generation Metadata")
        md.append(f"- **Generation Time:** {duration:.2f}s")
        md.append(f"- **LLM Calls:** {self.meta_stats['llm_calls']}")
        md.append(f"- **Total Analysis Tokens:** {self.meta_stats['total_tokens']}")
        md.append(f"- **Analysis Errors:** {self.meta_stats['errors']}")
        md.append("\n")

        return "\n".join(md)

    def _load_attempt_cache(self, run_dir: Path) -> Optional[List[tuple]]:
        """Loads cached attempt analysis results."""
        cache_path = run_dir / "attempt_analysis.json"
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            results = []
            for item in data:
                insight = ForensicInsight.model_validate(item["insight"])
                # Deserialize composite key "gen::case" -> (gen, case)
                key_parts = item["case_id"].split("::", 1)
                if len(key_parts) == 2:
                    results.append(((key_parts[0], key_parts[1]), insight))
                else:
                    # Fallback for old cache format (just case name)
                    # We can't recover generator name easily, so we might drop it or map to unknown
                    # For safety, let's invalidate old cache by ignoring
                    print(
                        f"Warning: Skipping invalid cache key format: {item['case_id']}"
                    )

            print(f"Loaded {len(results)} attempt insights from cache.")
            return results
        except Exception as e:
            print(f"Error loading attempt cache: {e}")
            return None

    def _save_attempt_cache(self, run_dir: Path, results: List[tuple]):
        """Saves attempt analysis results to cache."""
        cache_path = run_dir / "attempt_analysis.json"
        try:
            data = []
            for key, insight in results:
                # key is (generator_name, benchmark_name)
                if insight:
                    data.append(
                        {
                            "case_id": f"{key[0]}::{key[1]}",
                            "insight": insight.model_dump(),
                        }
                    )

            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Saved {len(data)} attempt insights to {cache_path}")
        except Exception as e:
            print(f"Error saving attempt cache: {e}")

    async def analyze_log_file(self, log_path: Path) -> str:
        """
        Analyzes the results and logs.
        """
        import time

        self.meta_stats["start_time"] = time.time()

        if not log_path.exists():
            return f"Log file not found: {log_path}"

        print(f"Analyzing run directory: {log_path.parent}")

        run_dir = log_path.parent
        generator_context = await self._load_static_context(run_dir)
        
        # Try YAML first (Standard Format)
        results_path = run_dir / "results.yaml"
        data = None
        
        if results_path.exists():
            try:
                try:
                    from yaml import CLoader as Loader
                except ImportError:
                    from yaml import Loader
                with open(results_path, "r", encoding="utf-8") as f:
                    data = yaml.load(f, Loader=Loader)
            except Exception as e:
                return f"Error loading results.yaml: {e}"
        else:
            # Fallback to JSON (Legacy)
            results_path = run_dir / "results.json"
            if not results_path.exists():
                return "No results.yaml or results.json found."
            
            try:
                with open(results_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                return f"Error loading results.json: {e}"

        try:
            TypeAdapter = pydantic.TypeAdapter(List[BenchmarkRunResult])
            results_list = TypeAdapter.validate_python(data)
            results_df = process_results(results_list)

            # Pre-calculate contexts
            quantitative_context = self._calculate_quantitative_stats(
                results_df, results_list
            )
            suite_context = self._get_suite_context(results_df)

        except Exception as e:
            print(f"Error processing results data: {e}")
            return f"Error processing results: {e}"

        # 1. Map: Analyze each Generator Independently
        generator_analyses: List[GeneratorAnalysisSection] = []
        generator_summaries_text = []  # For the high-level insights prompt

        # Calculate tool stats globally first to filter by generator later
        try:
            tool_df_all = get_tool_success_stats(results_list)
        except Exception:
            tool_df_all = pd.DataFrame()

        grouped = results_df.groupby("answer_generator")
        print(f"Identified {len(grouped)} generators.")

        for gen_name, _ in grouped:
            gen_results = [r for r in results_list if r.answer_generator == gen_name]
            log_text = await self._format_generator_logs(
                generator_name=gen_name, results_list=gen_results
            )

            # Filter tool stats for this specific generator
            gen_tool_stats = ""
            try:
                gen_tool_df = get_tool_success_stats(gen_results)
                if not gen_tool_df.empty:
                    gen_tool_stats = format_as_markdown(gen_tool_df)
            except Exception as e:
                print(
                    f"{Bcolors.FAIL}Error calculating tool stats for {gen_name}: {e}{Bcolors.ENDC}"
                )

            print(f"  {Bcolors.OKBLUE}Analyzing {gen_name}...{Bcolors.ENDC}")
            analysis = await self._analyze_generator(
                generator_name=gen_name,
                log_text=log_text,
                tool_stats_text=gen_tool_stats,
            )
            # FORCE override generator name to prevent LLM hallucinations/license text injection
            analysis.generator_name = gen_name
            generator_analyses.append(analysis)

            # Create a brief summary text for the high-level prompt
            generator_summaries_text.append(
                f"Generator: {gen_name}\nSummary: {analysis.performance_summary}"
            )

        # 2. Reduce: Generate High-Level Insights
        print(f"\n{Bcolors.HEADER}Generating high-level insights...{Bcolors.ENDC}")
        insights = await self._generate_high_level_insights(
            generator_summaries="\n\n".join(generator_summaries_text),
            quantitative_context=quantitative_context,
        )

        # 2.5 Generate Forensic Analysis
        print(f"\n{Bcolors.HEADER}Running forensic analysis...{Bcolors.ENDC}")
        forensic_context = ""
        try:
            run_analysis = analyze_benchmark_run(run_dir.name)

            # --- AI ANALYSIS PHASE (Map-Reduce) ---

            def is_infrastructure_error(case):
                err = str(case.final_validation_error).lower()
                return "429" in err or "resourceexhausted" in err or "quota" in err

            infra_failures = [
                c
                for c in run_analysis.cases
                if c.result_score == 0 and is_infrastructure_error(c)
            ]

            target_cases = [
                c
                for c in run_analysis.cases
                if c.result_score == 0
                and c.primary_failure_category
                in [
                    "Generic Failure",
                    "Unknown",
                    "Output Validation Error",
                    "Incorrect Answer (MC)",
                ]
                and not is_infrastructure_error(c)
            ]

            # --- LEVEL 1: MAP (Attempt Analysis) ---
            attempt_results = self._load_attempt_cache(run_dir)

            if attempt_results is None:
                if target_cases:
                    print(
                        f"  {Bcolors.WARNING}Deep diving into {len(target_cases)} complex failure cases (Map-Reduce)...{Bcolors.ENDC}"
                    )
                    tasks = []
                    sem = asyncio.Semaphore(10)

                    async def map_attempt(case, idx, attempt):
                        async with sem:
                            print(
                                f"    {Bcolors.OKCYAN}Mapping case: {case.benchmark_name} (Attempt {idx+1})...{Bcolors.ENDC}"
                            )
                            insight = await self._analyze_attempt(
                                case.benchmark_name, idx + 1, attempt
                            )
                            # Return composite key
                            return ((case.generator, case.benchmark_name), insight)

                    for case in target_cases:
                        for i, attempt in enumerate(case.attempts):
                            tasks.append(map_attempt(case, i, attempt))

                    attempt_results = await asyncio.gather(*tasks)
                    self._save_attempt_cache(run_dir, attempt_results)
                else:
                    attempt_results = []

            # Group insights
            from collections import defaultdict

            case_insights_map = defaultdict(list)
            for key, insight in attempt_results:
                if insight:
                    case_insights_map[key].append(insight)

            # --- LEVEL 2: REDUCE (Case Analysis) ---
            reduce_tasks = []

            async def reduce_case(key, case_insights):
                # key is (gen, name)
                print(
                    f"    {Bcolors.OKCYAN}Reducing case: {key[1]} ({len(case_insights)} attempts)...{Bcolors.ENDC}"
                )
                summary = await self._reduce_case_insights(key[1], case_insights)
                return (key, summary)

            for key, case_insights in case_insights_map.items():
                reduce_tasks.append(reduce_case(key, case_insights))

            case_summaries_list = await asyncio.gather(*reduce_tasks)
            # Map: (gen, name) -> Summary
            case_summary_map = {
                key: summary for key, summary in case_summaries_list if summary
            }

            # --- LEVEL 3: GENERATOR SUMMARY ---
            gen_case_groups = defaultdict(list)
            for key, summary in case_summary_map.items():
                gen_name = key[0]  # Extract generator from composite key
                gen_case_groups[gen_name].append(summary)

            gen_summary_map = {}
            for gen_name, summaries in gen_case_groups.items():
                print(
                    f"    {Bcolors.OKCYAN}Summarizing forensic patterns for generator: {gen_name}...{Bcolors.ENDC}"
                )
                gen_summary_map[gen_name] = await self._summarize_generator_forensics(
                    gen_name, summaries
                )

            # --- REPORT ASSEMBLY (Unified) ---

            lines = []

            if infra_failures:
                lines.append(
                    f"\n### ⚠️ Infrastructure Alerts\n- **{len(infra_failures)} cases** failed due to Rate Limits (429) or Quota Exhaustion. These were excluded from deep analysis."
                )

            for gen_name, gen_analysis in run_analysis.generators.items():
                lines.append(f"### Generator: {gen_name}")
                lines.append(
                    f"- **Pass Rate:** {gen_analysis.pass_rate:.1f}% ({gen_analysis.passed_cases}/{gen_analysis.total_cases})"
                )
                lines.append(f"- **Avg Latency:** {gen_analysis.avg_latency:.2f}s")
                lines.append(f"- **Est. Cost:** ${gen_analysis.estimated_cost:.3f}")

                # 1. Inject AI Generator Summary
                if gen_name in gen_summary_map:
                    ai_gen = gen_summary_map[gen_name]
                    lines.append("\n> **🧠 AI Root Cause Analysis (Generator Level)**")
                    lines.append(
                        f"> **Common Failure Patterns:** {ai_gen.common_failure_patterns}"
                    )
                    lines.append(
                        f"> **Critical Anti-Patterns:** {ai_gen.critical_anti_patterns}"
                    )
                    lines.append("> **Strategic Recommendations:**")
                    for rec in ai_gen.strategic_recommendations:
                        lines.append(f"> * {rec}")
                    lines.append("\n")

                # 2. List Failed Cases
                failed_cases = sorted(
                    [c for c in gen_analysis.cases if c.result_score == 0],
                    key=lambda x: x.benchmark_name,
                )

                if failed_cases:
                    lines.append(f"#### Failed Cases ({len(failed_cases)})")

                    for case in failed_cases:
                        lines.append(f"##### `{case.benchmark_name}`")

                        # Fetch one-liner for forensic context
                        # We use the prompt from the first attempt if available, otherwise raw_data
                        prompt_text = (
                            case.attempts[0].question
                            if case.attempts and case.attempts[0].question
                            else case.raw_data.get("prompt", "")
                        )
                        one_liner = await CASE_DOC_MANAGER.get_one_liner(
                            case.benchmark_name, prompt_text, self.model_name
                        )
                        lines.append(f'> *"{one_liner}"*')

                        # Composite key for this case
                        comp_key = (gen_name, case.benchmark_name)

                        # 2a. Inject AI Case Summary
                        if comp_key in case_summary_map:
                            ai_case = case_summary_map[comp_key]
                            lines.append(
                                f"- **Failure Pattern:** {ai_case.failure_pattern}"
                            )
                            lines.append(f"- **Progression:** {ai_case.progression}")
                            if ai_case.key_evidence:
                                lines.append(
                                    "- **Key Evidence:** "
                                    + ", ".join(ai_case.key_evidence)
                                )
                        else:
                            lines.append(
                                f"- **Error Category:** {case.primary_failure_category}"
                            )

                        # 2b. Attempt Details (Static + AI Insight per attempt)
                        for i, att in enumerate(case.attempts):
                            lines.append(f"\n**Attempt {i+1}:**")

                            # Inject AI Insight for this attempt
                            if comp_key in case_insights_map and i < len(
                                case_insights_map[comp_key]
                            ):
                                insight = case_insights_map[comp_key][i]
                                lines.append(
                                    f"- **Root Cause:** {insight.root_cause_category}"
                                )
                                lines.append(
                                    f"- **Failure Point:** {insight.dag_failure_point}"
                                )
                                lines.append(
                                    f"- **Explanation:** {insight.explanation}"
                                )

                            # Static Details (Diffs)
                            if att.ground_truth or att.answer:
                                lines.append("\n> **Expected vs Actual**")
                                gt_block = f"```\n{att.ground_truth}\n```".replace(
                                    "\n", "\n> "
                                )
                                lines.append(f"> **Expected:**\n> {gt_block}")
                                ans_block = f"```\n{att.answer}\n```".replace(
                                    "\n", "\n> "
                                )
                                lines.append(f"> **Actual:**\n> {ans_block}")

                            # Tool Chain Summary (Detailed)
                            if att.tools_used:
                                lines.append(f"- **Tool Chain:**")
                                for t in att.tools_used:
                                    t_name = t.get("name", "unknown")
                                    t_args = str(t.get("args", ""))
                                    t_out = str(t.get("output", ""))

                                    # Truncate
                                    if len(t_args) > 500:
                                        t_args = t_args[:497] + "..."
                                    if len(t_out) > 500:
                                        t_out = t_out[:497] + "..."

                                    lines.append(f"  - `{t_name}`")
                                    if t_args and t_args != "None":
                                        lines.append(f"    - Input: `{t_args}`")
                                    if t_out and t_out != "None":
                                        lines.append(f"    - Output: `{t_out}`")

                        lines.append("\n---\n")
                else:
                    lines.append("\n*No failures detected for this generator.*\n")

                lines.append("\n")

            forensic_context = "\n".join(lines)

            # --- EXPORT STRUCTURED DATA FOR VIEWER ---
            try:
                # Need to serialize composite keys for JSON (tuple -> string)
                # Map keys: (gen, name) -> "gen::name"
                json_cases = {f"{k[0]}::{k[1]}": v for k, v in case_summary_map.items()}
                json_attempts = {
                    f"{k[0]}::{k[1]}": v for k, v in case_insights_map.items()
                }

                forensic_data = ForensicData(
                    generators=gen_summary_map, cases=json_cases, attempts=json_attempts
                )
                data_path = run_dir / "forensic_data.json"
                with open(data_path, "w") as f:
                    f.write(forensic_data.model_dump_json(indent=2))
                print(f"Saved structured forensic data to {data_path}")
            except Exception as e:
                print(f"Error saving forensic_data.json: {e}")

        except Exception as e:
            print(f"Error running forensic analysis: {e}")
            import traceback

            traceback.print_exc()
            forensic_context += f"\n\n**Forensic Error:** {e}"

        # 3. Assemble Final Report
        print(f"\n{Bcolors.OKGREEN}Assembling final report...{Bcolors.ENDC}")
        print(f"[DEBUG] Type of insights: {type(insights)}")
        # print(f"[DEBUG] Insights content: {insights}")

        final_markdown = self._assemble_report(
            insights=insights,
            generator_analyses=generator_analyses,
            static_context=generator_context,
            quantitative_context=quantitative_context,
            suite_context=suite_context,
            forensic_context=forensic_context,
        )

        return final_markdown


async def analyze_run_logs(run_dir: Path, model_name: str):
    """
    Helper function to run the analyzer on a specific directory.
    """
    # Ensure full path
    if not run_dir.exists():
        potential = BENCHMARK_RUNS_DIR / run_dir
        if potential.exists():
            run_dir = potential

    log_path = run_dir / "trace.yaml"
    analyzer = LogAnalyzer(model_name=model_name)
    print(f"\n--- Starting Log Analysis on {run_dir} ---")
    print(f"Using Model: {model_name}")
    summary = await analyzer.analyze_log_file(log_path=log_path)

    analysis_path = run_dir / "log_analysis.md"
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"\n--- Log Analysis Complete ---")
    print(f"Report saved to: {analysis_path}")

    lines = summary.splitlines()
    print("\nSummary Preview:")
    print("\n".join(lines[:20]))


def get_latest_run():
    """Finds the most recently modified run directory."""
    runs_dir = BENCHMARK_RUNS_DIR
    if not runs_dir.exists():
        return None
    runs = sorted(
        [d for d in runs_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime
    )
    return runs[-1].name if runs else None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Benchmark Report")
    parser.add_argument(
        "run_id", nargs="?", help="Run ID or Directory (defaults to latest)"
    )
    parser.add_argument(
        "--model-name",
        default=MOST_POWERFUL_MODEL,
        help=f"LLM Model Name (default: {MOST_POWERFUL_MODEL})",
    )

    args = parser.parse_args()

    run_id = args.run_id or get_latest_run()
    if not run_id:
        print("Error: No benchmark runs found in benchmark_runs/")
        sys.exit(1)

    run_dir_path = Path(run_id)
    asyncio.run(analyze_run_logs(run_dir=run_dir_path, model_name=args.model_name))