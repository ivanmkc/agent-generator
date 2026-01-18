import json
import pathlib
from typing import List, Dict, Any
from collections import defaultdict

from tools.analysis.analyze_case import analyze_case, CaseAnalysis
from tools.analysis.analyze_generator import analyze_generator, GeneratorAnalysis

class BenchmarkRunAnalysis:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.run_dir = pathlib.Path("benchmark_runs") / run_id
        self.results_path = self.run_dir / "results.json"
        
        self.cases: List[CaseAnalysis] = []
        self.generators: Dict[str, GeneratorAnalysis] = {}
        
        if self.results_path.exists():
            self._load_and_process()

    def _load_and_process(self):
        with open(self.results_path, "r") as f:
            data = json.load(f)
            
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
                alerts.append({
                    "case": case.benchmark_name,
                    "generator": case.generator,
                    "reasons": [
                        "Sanitizer Hallucination" if any(a.has_sanitizer_hallucination for a in case.attempts) else None,
                        "Early Loop Exit" if any(a.loop_early_exit for a in case.attempts) else None
                    ]
                })
        return [a for a in alerts if any(a["reasons"])]

def analyze_benchmark_run(run_id: str) -> BenchmarkRunAnalysis:
    return BenchmarkRunAnalysis(run_id)
