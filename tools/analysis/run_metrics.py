"""
Orchestrator for benchmark run analysis.

This module provides the entry point for parsing and analyzing a complete benchmark
execution run. It loads the raw `results.json` artifact, instantiates analysis objects
for individual cases, and aggregates metrics across all generators used in the run.

It serves as the data layer for the CLI reporting tools and the Streamlit viewer.
"""

import json
import yaml
import gzip
import pathlib
from typing import List, Dict, Any
from collections import defaultdict

from tools.analysis.case_inspection import analyze_case, CaseAnalysis
from tools.analysis.generator_performance import analyze_generator, GeneratorAnalysis


class BenchmarkRunAnalysis:
    def __init__(self, run_id: str, runs_dir: pathlib.Path | None = None):
        self.run_id = run_id
        # Allow overriding base dir (useful for tools passing a Path object differently)
        base_dir = runs_dir if runs_dir else pathlib.Path("benchmark_runs")
        self.run_dir = base_dir / run_id
        
        self.cases: List[CaseAnalysis] = []
        self.generators: Dict[str, GeneratorAnalysis] = {}
        
        self._load_and_process()

    def _load_and_process(self):
        data = []
        
        # Try Gzipped JSON first (Primary)
        path_gz = self.run_dir / "results.json.gz"
        if path_gz.exists():
            try:
                with gzip.open(path_gz, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Error loading results.json.gz: {e}")

        if not data:
            # Fallback to JSON (Legacy)
            json_path = self.run_dir / "results.json"
            if json_path.exists():
                try:
                    with open(json_path, "r") as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"Error loading results.json: {e}")

        # Fallback to YAML (Legacy/Standard)
        if not data:
            yaml_path = self.run_dir / "results.yaml"
            if yaml_path.exists():
                try:
                    try:
                        from yaml import CLoader as Loader
                    except ImportError:
                        from yaml import Loader
                    with open(yaml_path, "r") as f:
                        data = yaml.load(f, Loader=Loader)
                except Exception as e:
                    print(f"Error loading results.yaml: {e}")
        
        if not data:
            print(f"Warning: No valid results found in {self.run_dir}")
            return

        # 1. Analyze every case
        self.cases = [analyze_case(c) for c in data]

        # 2. Group by generator and analyze
        gen_groups = defaultdict(list)
        for case in self.cases:
            gen_groups[case.generator].append(case)

        for gen_name, cases in gen_groups.items():
            self.generators[gen_name] = analyze_generator(gen_name, cases)

    @property
    def total_failures(self) -> int:
        return sum(g.failed_cases for g in self.generators.values())

    def get_critical_alerts(self) -> List[Dict[str, Any]]:
        """Finds cases with architectural bugs (Hallucinations/Loop Exits)."""
        alerts = []
        for case in self.cases:
            if case.result_score == 0 and case.has_critical_heuristic_failure:
                alerts.append(
                    {
                        "case": case.benchmark_name,
                        "generator": case.generator,
                        "reasons": [
                            "Sanitizer Hallucination"
                            if any(a.has_sanitizer_hallucination for a in case.attempts)
                            else None,
                            "Early Loop Exit"
                            if any(a.loop_early_exit for a in case.attempts)
                            else None,
                        ],
                    }
                )
        return [a for a in alerts if any(a["reasons"])]

def analyze_benchmark_run(run_id: str, runs_dir: pathlib.Path | None = None) -> BenchmarkRunAnalysis:
    return BenchmarkRunAnalysis(run_id, runs_dir)