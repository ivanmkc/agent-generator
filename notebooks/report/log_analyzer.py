import asyncio
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
import pydantic

# Add project root to sys.path to allow imports from benchmarks when running directly
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from google.genai import Client, types
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType
from benchmarks.data_models import BenchmarkRunResult
from benchmarks.analysis import (
    process_results,
    get_token_usage_stats,
    get_tool_success_stats,
    format_as_markdown
)

class LogAnalyzer:
    """
    Analyzes benchmark logs using Gemini to provide insights and summaries.
    Uses pandas to group results by Generator -> Suite -> Case -> Attempt.
    """

    def __init__(self, model_name: str = "gemini-3-pro-preview"):
        self.model_name = model_name

    def _get_client(self):
        """Initializes the Gemini client with a rotated API key."""
        api_key = API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)
        if not api_key:
            raise ValueError("No API key available for LogAnalyzer.")
        return Client(api_key=api_key)

    async def _generate_content(self, prompt: str) -> str:
        """Generates content using the Gemini API."""
        client = self._get_client()
        response = await client.aio.models.generate_content(
            model=self.model_name,
            contents=[types.Content(parts=[types.Part(text=prompt)])]
        )
        return response.text

    def _parse_generator_internals(self, md_content: str) -> Dict[str, str]:
        """Parses the generator_internals.md content into a dict of archetype -> description."""
        archetypes = {}
        current_key = None
        current_lines = []
        
        for line in md_content.splitlines():
            if line.startswith("### "):
                if current_key:
                    archetypes[current_key] = "\n".join(current_lines).strip()
                current_key = line.strip().replace("### ", "")
                current_lines = []
            elif current_key:
                current_lines.append(line)
                
        if current_key:
            archetypes[current_key] = "\n".join(current_lines).strip()
            
        return archetypes

    def _get_archetype_key_from_meta(self, gen_meta: Dict[str, Any]) -> str:
        """Reconstructs the archetype key from generator metadata."""
        image_name = gen_meta.get("image_name")
        name = gen_meta.get("name", "")
        
        if image_name:
            return f"GeminiCliPodman: {image_name}"
        
        # Fallback for ADK/Other: usually name prefix before parens
        if "(" in name:
            return name.split("(")[0]
        return name

    def _load_static_context(self, run_dir: Path) -> str:
        """
        Loads and merges run_metadata.json (runtime params) and generator_internals.md (static scaffolding).
        """
        metadata_path = run_dir / "run_metadata.json"
        # Look for the file in the run directory first, then fallback to the report directory
        internals_path = run_dir / "generator_internals.md"
        if not internals_path.exists():
             # Fallback to the source location if not copied to run dir yet (e.g. during dev)
             internals_path = Path("notebooks/report/generator_internals.md")
        
        if not metadata_path.exists():
            return "No run metadata found."
            
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            return f"Error loading run_metadata.json: {e}"

        archetypes = {}
        if internals_path.exists():
            try:
                with open(internals_path, "r", encoding="utf-8") as f:
                    archetypes = self._parse_generator_internals(f.read())
            except Exception as e:
                print(f"Error loading generator_internals.md: {e}")

        # Construct Context
        context_parts = ["# Generator Internals (Runtime Actualized)\n"]
        generators = meta.get("generators", [])
        
        for gen in generators:
            name = gen.get("name", "Unknown")
            model = gen.get("model_name", "Unknown")
            key = self._get_archetype_key_from_meta(gen)
            
            context_parts.append(f"### {name}")
            
            # Inject Description from Archetype
            if key in archetypes:
                desc = archetypes[key]
                # Replace placeholder
                desc = desc.replace("[Injected at Runtime]", model)
                context_parts.append(desc)
            else:
                context_parts.append(f"**Model:** `{model}`")
                context_parts.append("\n(No detailed static description found for this generator archetype.)\n")
            
            context_parts.append("---\n")
            
        return "\n".join(context_parts)

    def _calculate_quantitative_stats(self, results_df: pd.DataFrame, results_list: List[BenchmarkRunResult]) -> str:
        """Calculates quantitative statistics from the results DataFrame."""
        if results_df.empty:
            return "No quantitative results available."

        stats_lines = ["### Quantitative Summary (Ground Truth)\n"]
        
        # Calculate token stats from logs
        token_df = get_token_usage_stats(results_list)
        
        # Group by generator and suite
        grouped = results_df.groupby(["answer_generator", "suite"])
        
        summary_data = []
        
        for (gen_name, suite_name), group in grouped:
            total_cases = len(group)
            passed_cases = group["result"].sum()
            case_pass_rate = (passed_cases / total_cases) * 100 if total_cases > 0 else 0
            
            # Calculate attempt-level stats
            all_attempts = []
            for att_list in group["generation_attempts"]:
                if isinstance(att_list, list):
                    all_attempts.extend(att_list)
            
            total_attempts = len(all_attempts)
            successful_attempts = sum(1 for a in all_attempts if (a.get('status') if isinstance(a, dict) else getattr(a, 'status', '')) == 'success')
            attempt_pass_rate = (successful_attempts / total_attempts) * 100 if total_attempts > 0 else 0
            
            # Calculate Avg Latency (Success Only)
            success_latency = group[group["result"] == 1]["latency"].mean()
            if pd.isna(success_latency): success_latency = 0.0
            
            # Calculate Avg Tokens (Success Only)
            avg_tokens = 0
            if not token_df.empty:
                # Filter for this generator
                gen_token_df = token_df[token_df["Generator"] == gen_name]
                # Filter for benchmarks in this suite that PASSED
                successful_benchmarks = group[group["result"] == 1]["benchmark_name"].unique()
                
                if len(successful_benchmarks) > 0 and not gen_token_df.empty:
                    # Sum tokens for these specific benchmark cases
                    relevant_tokens = gen_token_df[gen_token_df["Benchmark"].isin(successful_benchmarks)]["Total Tokens"].sum()
                    avg_tokens = relevant_tokens / len(successful_benchmarks)
            
            # Total Cost (All attempts)
            total_tokens_all = 0
            if not token_df.empty:
                # Filter for this generator and suite benchmarks (all attempts)
                suite_benchmarks = group["benchmark_name"].unique()
                gen_suite_tokens = token_df[
                    (token_df["Generator"] == gen_name) & 
                    (token_df["Benchmark"].isin(suite_benchmarks))
                ]
                total_tokens_all = gen_suite_tokens["Total Tokens"].sum()
            
            # Cost Estimate: $0.10 per 1M tokens (Blended Input/Output for Gemini 2.5 Flash)
            estimated_cost = (total_tokens_all / 1_000_000) * 0.10

            summary_data.append({
                "Generator": gen_name,
                "Suite": suite_name,
                "Cases": total_cases,
                "Passed": passed_cases,
                "Case Pass Rate": f"{case_pass_rate:.1f}%",
                "Total Attempts": total_attempts,
                "Attempt Success Rate": f"{attempt_pass_rate:.1f}%",
                "Avg Latency (Success)": f"{success_latency:.2f}s",
                "Avg Tokens (Success)": f"{avg_tokens:.0f}",
                "Est. Cost": f"${estimated_cost:.4f}"
            })
            
        summary_df = pd.DataFrame(summary_data)
        stats_lines.append(format_as_markdown(summary_df))
        
        stats_lines.append("\n*Note: 'Avg Latency' and 'Avg Tokens' are calculated per successful benchmark case. 'Est. Cost' includes all attempts (success + failure) assuming a blended rate of $0.10 per 1M tokens.*\n")

        # Tool Success Rates
        stats_lines.append("\n#### Tool Success Rates\n")
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
                stats_lines.append(format_as_markdown(tool_df))
            else:
                stats_lines.append("No tool usage detected.")
        except Exception as e:
            stats_lines.append(f"Error calculating tool stats: {e}")
        
        return "\n".join(stats_lines)

    def _format_generator_logs(self, generator_name: str, results_list: List[BenchmarkRunResult]) -> str:
        """
        Formats the execution logs for a specific generator into a structured text block for the LLM.
        Groups by Suite -> Case -> Attempts.
        """
        lines = [f"GENERATOR: {generator_name}"]
        
        # Convert to DF for easier grouping
        df = pd.DataFrame([r.model_dump() for r in results_list])
        
        if df.empty:
            return f"No results found for generator: {generator_name}"

        # Clean suite names
        if "suite" in df.columns:
            df["suite"] = df["suite"].apply(lambda x: Path(x).parent.name)
        else:
            df["suite"] = "unknown_suite"

        for suite_name, suite_group in df.groupby("suite"):
            lines.append(f"\nSUITE: {suite_name}")
            
            for _, row in suite_group.iterrows():
                case_name = row["benchmark_name"]
                result = "PASS" if row["result"] == 1 else "FAIL"
                icon = "✅" if row["result"] == 1 else "❌"
                
                lines.append(f"\n  CASE: {case_name} -> {icon} {result}")
                
                if row["validation_error"]:
                    lines.append(f"    Validation Error: {row['validation_error']}")
                
                # Attempts
                attempts = row.get("generation_attempts", [])
                if attempts:
                    lines.append("    Attempts:")
                    for att in attempts:
                        # Handle attempt being dict (from model_dump) or object
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
                            
                        lines.append(f"      Attempt {a_num}: {a_status.upper()} ({a_dur:.2f}s)")
                        if a_err:
                            lines.append(f"        Error: {a_err}")
                            
        return "\n".join(lines)

    async def _analyze_generator(self, generator_name: str, log_text: str) -> str:
        """
        Analyzes the logs for a single generator.
        """
        prompt_path = Path("notebooks/report/log_analysis_node_prompt.md")
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        else:
             prompt_template = "Analyze this generator execution: {log_text}"

        prompt = prompt_template.format(node_name=generator_name, log_text=log_text)

        try:
            text = await self._generate_content(prompt)
            return f"### Analysis of '{generator_name}'\n\n{text}"
        except Exception as e:
            print(f"Error analyzing generator {generator_name}: {e}")
            return f"Error analyzing generator {generator_name}: {e}"

    async def _reduce_analyses(self, analyses: List[str], static_context: str = "", quantitative_context: str = "") -> str:
        """
        Aggregates per-node analyses into a final report.
        """
        combined_text = "\n\n".join(analyses)
        
        # Load prompt from external file
        prompt_path = Path("notebooks/report/log_analysis_reduce_prompt.md")
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        else:
             prompt_template = "Synthesize these analyses: {combined_text}"

        # If the template doesn't have the placeholder, append context manually
        if "{quantitative_context}" not in prompt_template:
             static_context += "\n\n" + quantitative_context
             formatted_quantitative = ""
        else:
             formatted_quantitative = quantitative_context

        prompt = prompt_template.format(
            combined_text=combined_text, 
            static_context=static_context,
            quantitative_context=formatted_quantitative
        )

        try:
            return await self._generate_content(prompt)
        except Exception as e:
            print(f"Error generating final summary: {e}")
            return "Failed to generate final summary."

    def _get_suite_context(self, results_df: pd.DataFrame) -> str:
        """Generates a description of the benchmark suites present in the results."""
        if results_df.empty:
            return ""
            
        suites = results_df["suite"].unique()
        suite_descs = []
        
        known_suites = {
            "api_understanding": "Tests the model's ability to recall correct import paths and class signatures without hallucination. Requires strict adherence to the ADK library structure.",
            "fix_errors": "Tests the model's ability to debug and fix broken code snippets using the ADK. Measures reasoning and self-correction.",
            "multiple_choice": "Tests general reasoning or specific knowledge selection from provided options."
        }
        
        for s in suites:
            desc = known_suites.get(s, "Custom benchmark suite.")
            suite_descs.append(f"### Suite: `{s}`\n*   **Objective:** {desc}")
            
        return "\n\n## Benchmark Suites\n" + "\n".join(suite_descs) + "\n"

    async def analyze_log_file(self, log_path: Path) -> str:
        """
        Analyzes the results and logs.
        """
        if not log_path.exists():
            return f"Log file not found: {log_path}"

        print(f"Analyzing run directory: {log_path.parent}")
        
        # Load Static Metadata
        run_dir = log_path.parent
        generator_context = self._load_static_context(run_dir)

        # Load Quantitative Results (results.json)
        results_path = run_dir / "results.json"
        
        if not results_path.exists():
            return "No results.json found. Cannot proceed with analysis."

        try:
            with open(results_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Parse into objects then dataframe
            TypeAdapter = pydantic.TypeAdapter(List[BenchmarkRunResult])
            results_list = TypeAdapter.validate_python(data)
            results_df = process_results(results_list)
            
            quantitative_context = self._calculate_quantitative_stats(results_df, results_list)
            
            # Append suite context to generator context
            suite_context = self._get_suite_context(results_df)
            generator_context += "\n" + suite_context
            
        except Exception as e:
            print(f"Error loading/processing results.json: {e}")
            return f"Error analyzing results: {e}"

        # 1. Map: Analyze each Generator
        tasks = []
        # Group by generator
        grouped = results_df.groupby("answer_generator")
        
        print(f"Identified {len(grouped)} generators. Starting parallel analysis...")
        
        for gen_name, _ in grouped:
            # Filter the list for this generator
            gen_results = [r for r in results_list if r.answer_generator == gen_name]
            
            # Format the logs/results for this generator
            log_text = self._format_generator_logs(generator_name=gen_name, results_list=gen_results)
            
            # Create analysis task
            tasks.append(self._analyze_generator(generator_name=gen_name, log_text=log_text))
        
        node_analyses = await asyncio.gather(*tasks)

        # 2. Reduce: Synthesize the final report
        final_summary = await self._reduce_analyses(
            analyses=node_analyses, 
            static_context=generator_context, 
            quantitative_context=quantitative_context
        )
        
        return final_summary

async def analyze_run_logs(run_dir: Path):
    """
    Helper function to run the analyzer on a specific directory.
    """
    log_path = run_dir / "trace.jsonl"
    analyzer = LogAnalyzer()
    print(f"\n--- Starting Log Analysis on {run_dir} ---")
    summary = await analyzer.analyze_log_file(log_path=log_path)
    
    # Save the analysis
    analysis_path = run_dir / "log_analysis.md"
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"\n--- Log Analysis Complete ---")
    print(f"Report saved to: {analysis_path}")
    
    # Print a preview
    lines = summary.splitlines()
    preview = "\n".join(lines[:20])
    print("\nSummary Preview:")
    print(preview)
    print("...")

if __name__ == "__main__":
    # Test block for running this script directly
    import sys
    if len(sys.argv) > 1:
        run_dir_path = Path(sys.argv[1])
        asyncio.run(analyze_run_logs(run_dir=run_dir_path))