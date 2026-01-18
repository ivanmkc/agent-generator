import asyncio
import os
import sys
import json
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
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType
from benchmarks.data_models import BenchmarkRunResult, TraceEventType
from benchmarks.analysis import (
    process_results,
    get_token_usage_stats,
    get_tool_success_stats,
    format_as_markdown
)
from tools.analysis.analyze_benchmark_run import analyze_benchmark_run
from tools.cli.audit_failures import get_report_content
from tools.analysis.doc_generator import DOC_MANAGER
from benchmarks.benchmark_candidates import CANDIDATE_GENERATORS

# --- Pydantic Models for Structured Report ---

class GeneratorAnalysisSection(BaseModel):
    generator_name: str = Field(..., description="Name of the generator.")
    performance_summary: str = Field(..., description="Summary of performance (Stability, Retry patterns, etc.).")
    docs_context_analysis: str = Field(..., description="Analysis of Docs/Context injection effectiveness.")
    tool_usage_analysis: str = Field(..., description="Analysis of tool usage effectiveness and errors.")
    general_error_analysis: str = Field(..., description="Analysis of general errors (logic, syntax, etc.) with embedded examples.")

class HighLevelInsights(BaseModel):
    executive_summary: str = Field(..., description="High-level overview of the session, organized by Generator and Suite.")
    cross_generator_comparison: str = Field(..., description="Comparison on Quality, Efficiency, Latency, and Stability.")
    recommendations: List[str] = Field(..., description="List of actionable recommendations.")

class ForensicInsight(BaseModel):
    root_cause_category: str = Field(..., description="The primary reason for failure (e.g. 'Hallucination', 'Retrieval Failure', 'Loop Exit').")
    dag_failure_point: str = Field(..., description="Where in the Agent DAG did it fail? (e.g., 'Retrieval Loop -> Tool Call', 'Implementation Planner -> Plan Generation').")
    explanation: str = Field(..., description="A precise narrative of why this specific attempt failed.")
    evidence: List[str] = Field(..., description="Specific log events supporting the conclusion.")

class CaseSummary(BaseModel):
    benchmark_name: str = Field(..., description="The name of the benchmark case.")
    failure_pattern: str = Field(..., description="The recurring failure mode across attempts (e.g. 'Persistent Hallucination', 'Flaky Tool Usage').")
    progression: str = Field(..., description="Did the agent improve, regress, or loop? (e.g. 'Regressed', 'Stuck', 'Oscillated').")
    key_evidence: List[str] = Field(..., description="Top 3 pieces of evidence summarizing the case failure.")

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
            "errors": 0
        }

    def _get_client(self):
        """Initializes the Gemini client with a rotated API key."""
        api_key = API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)
        if not api_key:
            raise ValueError("No API key available for LogAnalyzer.")
        return Client(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=20),
        retry=retry_if_exception_type(Exception) # The SDK usually raises generic Exception or specific APIError
    )
    async def _generate_content(self, prompt: str, schema: Any = None) -> Any:
        """Generates content using the Gemini API, optionally enforcing a schema."""
        self.meta_stats["llm_calls"] += 1
        client = self._get_client()
        
        config = {}
        if schema:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema
            )

        response = await client.aio.models.generate_content(
            model=self.model_name,
            contents=[types.Content(parts=[types.Part(text=prompt)])],
            config=config
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

    def _load_static_context(self, run_dir: Path) -> str:
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

        context_parts = ["# Generator Internals (Runtime Actualized)\n"]
        generators_meta = meta.get("generators", [])
        
        # Build a lookup map for candidate objects by name
        # Note: CANDIDATE_GENERATORS contains the current code definitions.
        # Ideally, we match by name.
        candidate_map = {g.name: g for g in CANDIDATE_GENERATORS}
        
        for gen_meta in generators_meta:
            name = gen_meta.get("name", "Unknown")
            model = gen_meta.get("model_name", "Unknown")
            key = self._get_archetype_key_from_meta(gen_meta)
            
            context_parts.append(f"### {name}")
            
            # Try to find the matching code object to generate docs if missing
            # Matches "ADK_HYBRID_V47(gemini-2.5-flash)" -> object
            # We need to match the *archetype* effectively.
            # The candidates list usually has specific instantiations.
            
            # Heuristic: Find a candidate that starts with the key
            candidate_obj = None
            for c_name, c_obj in candidate_map.items():
                if key in c_name:
                    candidate_obj = c_obj
                    break
            
            if candidate_obj:
                # This call will check cache, generate if missing, and return desc
                desc = DOC_MANAGER.get_description(key, candidate_obj, self.model_name)
                desc = desc.replace("[Injected at Runtime]", model)
                context_parts.append(desc)
            else:
                context_parts.append(f"**Model:** `{model}`")
                context_parts.append(f"**Archetype Key:** `{key}`")
                context_parts.append("\n(No code definition found for this generator to analyze.)\n")
            
            context_parts.append("\n")
            
        return "\n".join(context_parts)

    def _calculate_quantitative_stats(self, results_df: pd.DataFrame, results_list: List[BenchmarkRunResult]) -> str:
        """Calculates quantitative statistics from the results DataFrame."""
        if results_df.empty:
            return "No quantitative results available."

        stats_lines = ["### 4. Quantitative Analysis\n"]
        
        stats_lines.append("#### Metric Definitions & Methodology\n")
        stats_lines.append("| Metric | Definition | Calculation |")
        stats_lines.append("| :--- | :--- | :--- |")
        stats_lines.append("| **Overall Pass Rate** | Percentage of benchmark cases where the generator produced a correct, passing answer (Score = 1). | `(Passed Cases / Total Cases) * 100` |")
        stats_lines.append("| **Avg Latency** | Average execution time for *passing* cases only. | `Mean(Duration)` of successful runs. |")
        stats_lines.append("| **Est. Cost** | Estimated total cost based on token usage across all attempts (success + fail). | `(Total Tokens / 1,000,000) * $0.10` (Blended Input/Output Rate for Gemini 2.5 Flash). |")
        stats_lines.append("\n")

        token_df = get_token_usage_stats(results_list)
        all_suites = sorted(results_df["suite"].unique())
        
        leaderboard_data = []
        for gen_name, group in results_df.groupby("answer_generator"):
            total_cases = len(group)
            passed_cases = group["result"].sum()
            pass_rate = (passed_cases / total_cases) * 100 if total_cases > 0 else 0
            
            success_latency = group[group["result"] == 1]["latency"].mean()
            if pd.isna(success_latency): success_latency = 0.0
            
            total_tokens = 0
            if not token_df.empty:
                gen_tokens = token_df[token_df["Generator"] == gen_name]
                total_tokens = gen_tokens["Total Tokens"].sum()
            
            cost = (total_tokens / 1_000_000) * 0.10
            
            entry = {
                "Generator": gen_name,
                "Overall Pass Rate": f"{pass_rate:.1f}%",
                "Avg Latency": f"{success_latency:.2f}s",
                "Est. Cost": f"${cost:.3f}"
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
            
        leaderboard_df = pd.DataFrame(leaderboard_data).sort_values("Overall Pass Rate", ascending=False)
        stats_lines.append(format_as_markdown(leaderboard_df))
        stats_lines.append("\n")

        # 3. Tool Success & Impact
        stats_lines.append("#### Tool Success & Impact\n")
        stats_lines.append("Methodology: 'Success Rate' is the % of tool calls without exceptions. 'Lift' compares case pass rates with vs. without tool usage.\n")
        
        try:
            tool_df = get_tool_success_stats(results_list)
            if not tool_df.empty:
                # Format percentages
                tool_df["success_rate"] = (tool_df["success_rate"] * 100).map("{:.1f}%".format)
                tool_df["lift"] = (tool_df["lift"] * 100).map("{:+.1f}%".format)
                # Rename columns for display
                tool_df = tool_df.rename(columns={
                    "tool": "Tool",
                    "times_used": "Times Used",
                    "successes": "Successes",
                    "success_rate": "Success Rate",
                    "lift": "Lift"
                })
                # Select relevant columns
                display_cols = ["Tool", "Times Used", "Success Rate", "Lift"]
                stats_lines.append(format_as_markdown(tool_df[display_cols]))
            else:
                stats_lines.append("No tool usage detected.")
        except Exception as e:
            stats_lines.append(f"Error calculating tool stats: {e}")
        stats_lines.append("\n")

        return "\n".join(stats_lines)

    def _format_generator_logs(self, generator_name: str, results_list: List[BenchmarkRunResult]) -> str:
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
                lines.append(f"\n[TRUNCATED REMAINING LOGS DUE TO SIZE LIMIT ({MAX_TOTAL_CHARS} chars)]")
                break
                
            total = len(suite_group)
            passed = suite_group["result"].sum()
            rate = (passed / total) * 100 if total > 0 else 0
            
            suite_header = f"\nSUITE: {suite_name} (Pass Rate: {rate:.1f}% - {passed}/{total})"
            lines.append(suite_header)
            current_chars += len(suite_header)
            
            for _, row in suite_group.iterrows():
                if current_chars > MAX_TOTAL_CHARS:
                    break
                    
                case_name = row["benchmark_name"]
                result = "PASS" if row["result"] == 1 else "FAIL"
                icon = "✅" if row["result"] == 1 else "❌"
                
                case_line = f"\n  CASE: {case_name} -> {icon} {result}"
                lines.append(case_line)
                current_chars += len(case_line)

                if row["result"] == 0:
                    gt = f"    Ground Truth: {row['ground_truth']}"
                    ans = f"    Model Answer: {str(row['answer'])[:200]}..."
                    lines.append(gt)
                    lines.append(ans)
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
                            
                        att_line = f"      Attempt {a_num}: {a_status.upper()} ({a_dur:.2f}s)"
                        lines.append(att_line)
                        current_chars += len(att_line)
                        
                        # Add tool usage summary
                        logs = att.get("trace_logs", []) if isinstance(att, dict) else (att.trace_logs or [])
                        
                        if logs:
                            tools_used = []
                            for log in logs:
                                t_type = log.get("type") if isinstance(log, dict) else log.type
                                t_name = log.get("tool_name") if isinstance(log, dict) else log.tool_name
                                if str(t_type) == "tool_use" and t_name:
                                    tools_used.append(t_name)
                            
                            if tools_used:
                                tool_line = f"        Tools Used: {', '.join(tools_used)}"
                                lines.append(tool_line)
                                current_chars += len(tool_line)
                        
                        if a_err:
                            # Filter out noisy [DEBUG] lines from logs
                            filtered_err_lines = [l for l in a_err.splitlines() if "[DEBUG]" not in l]
                            a_err = "\n".join(filtered_err_lines)

                            if len(a_err) > MAX_ERROR_CHARS:
                                a_err = a_err[:MAX_ERROR_CHARS] + f" ... [TRUNCATED {len(a_err) - MAX_ERROR_CHARS} chars]"
                            
                            err_line = f"        Error Output:\n{a_err}"
                            lines.append(err_line)
                            current_chars += len(err_line)
                            
        return "\n".join(lines)

    async def _analyze_generator(self, generator_name: str, log_text: str, tool_stats_text: str = "") -> GeneratorAnalysisSection:
        """
        Analyzes the logs for a single generator and returns a structured object.
        """
        
        tool_context = f"\nComputed Tool Usage Stats for this Generator:\n{tool_stats_text}\n" if tool_stats_text else ""

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
                general_error_analysis=f"Analysis Failed: {str(e)}"
            )

    async def _generate_high_level_insights(self, generator_summaries: str, quantitative_context: str) -> HighLevelInsights:
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
                recommendations=["Failed to generate."]
            )

    async def _analyze_attempt(self, case_name: str, attempt_idx: int, attempt_analysis: Any) -> Optional[ForensicInsight]:
        """Uses LLM to perform deep forensic analysis on a single attempt."""
        
        # Serialize trace (truncate if huge)
        trace_events = []
        for evt in attempt_analysis.trace_logs:
            trace_events.append({
                "author": evt.get("author"),
                "tool": evt.get("tool_name"),
                "input": str(evt.get("tool_input"))[:200],
                "output": str(evt.get("tool_output"))[:200],
                "thought": str(evt.get("content"))[:300]
            })
            
        trace_str = json.dumps(trace_events, indent=2)
        if len(trace_str) > 50000:
            trace_str = trace_str[:25000] + "\n...[TRUNCATED]...\n" + trace_str[-25000:]
            
        prompt = FORENSIC_PROMPT.format(
            benchmark_name=case_name,
            error_message=attempt_analysis.error_message,
            trace_json=trace_str
        )
        
        try:
            return await self._generate_content(prompt, schema=ForensicInsight)
        except Exception as e:
            print(f"LLM Analysis failed for {case_name} (Attempt {attempt_idx}): {e}")
            return None

    async def _reduce_case_insights(self, case_name: str, attempt_insights: List[ForensicInsight]) -> Optional[CaseSummary]:
        """Reduces multiple attempt insights into a single case summary (Level 2)."""
        if not attempt_insights:
            return None
            
        insights_json = json.dumps([i.model_dump() for i in attempt_insights], indent=2)
        
        prompt = CASE_REDUCTION_PROMPT.format(
            benchmark_name=case_name,
            insights_json=insights_json
        )
        
        try:
            return await self._generate_content(prompt, schema=CaseSummary)
        except Exception as e:
            print(f"Case Reduction failed for {case_name}: {e}")
            return None

    def _get_suite_context(self, results_df: pd.DataFrame) -> str:
        """Generates a table of benchmark suites and their objectives."""
        if results_df.empty:
            return ""
            
        suites = results_df["suite"].unique()
        
        known_suites = {
            "api_understanding": "Tests the model's ability to recall correct import paths and class signatures without hallucination. Requires strict adherence to the ADK library structure.",
            "fix_errors": "Tests the model's ability to debug and fix broken code snippets using the ADK. Measures reasoning and self-correction.",
            "multiple_choice": "Tests general reasoning or specific knowledge selection from provided options."
        }
        
        suite_data = []
        for s in suites:
            desc = "Custom benchmark suite."
            if "api_understanding" in s: desc = known_suites["api_understanding"]
            elif "fix_errors" in s: desc = known_suites["fix_errors"]
            elif "_mc" in s: desc = known_suites["multiple_choice"]
            
            suite_data.append({
                "Suite": f"`{s}`",
                "Objective": desc
            })
            
        suite_df = pd.DataFrame(suite_data)
            
        return "\n\n## Benchmark Suites Overview\n" + format_as_markdown(suite_df) + "\n"

    def _assemble_report(self, 
                         insights: HighLevelInsights, 
                         generator_analyses: List[GeneratorAnalysisSection], 
                         static_context: str, 
                         quantitative_context: str,
                         suite_context: str,
                         forensic_context: str = "") -> str:
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
            md.append(forensic_context)
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
        generator_context = self._load_static_context(run_dir)
        
        results_path = run_dir / "results.json"
        
        if not results_path.exists():
            return "No results.json found."

        try:
            with open(results_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            TypeAdapter = pydantic.TypeAdapter(List[BenchmarkRunResult])
            results_list = TypeAdapter.validate_python(data)
            results_df = process_results(results_list)
            
            # Pre-calculate contexts
            quantitative_context = self._calculate_quantitative_stats(results_df, results_list)
            suite_context = self._get_suite_context(results_df)
            
        except Exception as e:
            print(f"Error loading/processing results.json: {e}")
            return f"Error analyzing results: {e}"

        # 1. Map: Analyze each Generator Independently
        generator_analyses: List[GeneratorAnalysisSection] = []
        generator_summaries_text = [] # For the high-level insights prompt
        
        # Calculate tool stats globally first to filter by generator later
        try:
            tool_df_all = get_tool_success_stats(results_list)
        except Exception:
            tool_df_all = pd.DataFrame()

        grouped = results_df.groupby("answer_generator")
        print(f"Identified {len(grouped)} generators.")
        
        for gen_name, _ in grouped:
            gen_results = [r for r in results_list if r.answer_generator == gen_name]
            log_text = self._format_generator_logs(generator_name=gen_name, results_list=gen_results)
            
            # Filter tool stats for this specific generator
            gen_tool_stats = ""
            try:
                gen_tool_df = get_tool_success_stats(gen_results)
                if not gen_tool_df.empty:
                    gen_tool_stats = format_as_markdown(gen_tool_df)
            except Exception as e:
                print(f"Error calculating tool stats for {gen_name}: {e}")

            print(f"Analyzing {gen_name}...")
            analysis = await self._analyze_generator(generator_name=gen_name, log_text=log_text, tool_stats_text=gen_tool_stats)
            generator_analyses.append(analysis)
            
            # Create a brief summary text for the high-level prompt
            generator_summaries_text.append(f"Generator: {gen_name}\nSummary: {analysis.performance_summary}")
        
        # 2. Reduce: Generate High-Level Insights
        print("Generating high-level insights...")
        insights = await self._generate_high_level_insights(
            generator_summaries="\n\n".join(generator_summaries_text),
            quantitative_context=quantitative_context
        )
        
        # 2.5 Generate Forensic Analysis
        print("Running forensic analysis...")
        forensic_context = ""
        try:
            run_analysis = analyze_benchmark_run(run_dir.name)
            
            # A. Deterministic Report
            if run_analysis.total_failures > 0:
                forensic_context = get_report_content(run_analysis)
            
            # B. LLM Hierarchical Deep Dive (Map-Reduce)
            # Filter criteria: 
            # 1. Failed
            # 2. Confusing category (Generic/Unknown)
            # 3. NOT an infrastructure error (429/Quota) to save cost/time
            
            def is_infrastructure_error(case):
                err = str(case.final_validation_error).lower()
                return "429" in err or "resourceexhausted" in err or "quota" in err

            infra_failures = [c for c in run_analysis.cases if c.result_score == 0 and is_infrastructure_error(c)]
            
            target_cases = [
                c for c in run_analysis.cases 
                if c.result_score == 0 
                and c.primary_failure_category in ["Generic Failure", "Unknown"]
                and not is_infrastructure_error(c)
            ]
            
            if infra_failures:
                print(f"Skipping {len(infra_failures)} infrastructure failures (429/Quota).")
                forensic_context += f"\n\n### ⚠️ Infrastructure Alerts\n- **{len(infra_failures)} cases** failed due to Rate Limits (429) or Quota Exhaustion. These were excluded from deep analysis."

            if target_cases:
                print(f"Deep diving into {len(target_cases)} complex failure cases (Map-Reduce)...")
                
                # --- LEVEL 1: MAP (Attempt Analysis) ---
                tasks = []
                sem = asyncio.Semaphore(10) # Higher concurrency for map phase
                
                async def map_attempt(case, idx, attempt):
                    async with sem:
                        insight = await self._analyze_attempt(case.benchmark_name, idx + 1, attempt)
                        return (case.benchmark_name, insight)

                for case in target_cases:
                    for i, attempt in enumerate(case.attempts):
                        tasks.append(map_attempt(case, i, attempt))
                
                attempt_results = await asyncio.gather(*tasks)
                
                # Group insights by case
                from collections import defaultdict
                case_insights_map = defaultdict(list)
                for name, insight in attempt_results:
                    if insight:
                        case_insights_map[name].append(insight)
                
                # --- LEVEL 2: REDUCE (Case Analysis) ---
                reduce_tasks = []
                
                async def reduce_case(name, case_insights):
                    summary = await self._reduce_case_insights(name, case_insights)
                    return (name, summary)

                for name, case_insights in case_insights_map.items():
                    reduce_tasks.append(reduce_case(name, case_insights))
                    
                case_summaries = await asyncio.gather(*reduce_tasks)
                
                # Format Level 2 Output
                llm_section = ["\n\n## 9. AI-Powered Root Cause Analysis (Hierarchical)"]
                
                for name, summary in case_summaries:
                    if summary:
                        llm_section.append(f"### `{name}`")
                        llm_section.append(f"- **Pattern:** {summary.failure_pattern}")
                        llm_section.append(f"- **Progression:** {summary.progression}")
                        if summary.key_evidence:
                            llm_section.append(f"- **Key Evidence:**")
                            for ev in summary.key_evidence:
                                llm_section.append(f"  - {ev}")
                        llm_section.append("---\n")
                
                if case_summaries:
                    forensic_context += "\n".join(llm_section)

        except Exception as e:
            print(f"Error running forensic analysis: {e}")
            import traceback
            traceback.print_exc()
            forensic_context += f"\n\n**Forensic Error:** {e}"
        
        # 3. Assemble Final Report
        print("Assembling final report...")
        print(f"[DEBUG] Type of insights: {type(insights)}")
        # print(f"[DEBUG] Insights content: {insights}")
        
        final_markdown = self._assemble_report(
            insights=insights,
            generator_analyses=generator_analyses,
            static_context=generator_context,
            quantitative_context=quantitative_context,
            suite_context=suite_context,
            forensic_context=forensic_context
        )
        
        return final_markdown

async def analyze_run_logs(run_dir: Path, model_name: str):
    """
    Helper function to run the analyzer on a specific directory.
    """
    # Ensure full path
    if not run_dir.exists():
        potential = Path("benchmark_runs") / run_dir
        if potential.exists():
            run_dir = potential
    
    log_path = run_dir / "trace.jsonl"
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
    runs_dir = Path("benchmark_runs")
    if not runs_dir.exists(): return None
    runs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime)
    return runs[-1].name if runs else None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Benchmark Report")
    parser.add_argument("run_id", nargs="?", help="Run ID or Directory (defaults to latest)")
    parser.add_argument("--model-name", required=True, help="LLM Model Name (e.g. gemini-3-pro-preview)")
    
    args = parser.parse_args()
    
    run_id = args.run_id or get_latest_run()
    if not run_id:
        print("Error: No benchmark runs found in benchmark_runs/")
        sys.exit(1)
        
    run_dir_path = Path(run_id)
    asyncio.run(analyze_run_logs(run_dir=run_dir_path, model_name=args.model_name))
