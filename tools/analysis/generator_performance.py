from typing import List, Dict, Any
from tools.analysis.case_inspection import CaseAnalysis

class GeneratorAnalysis:
    def __init__(self, generator_name: str, cases: List[CaseAnalysis]):
        self.name = generator_name
        self.cases = cases
        
        # Computed Metrics
        self.total_cases = len(cases)
        self.passed_cases = sum(1 for c in cases if c.result_score == 1)
        self.failed_cases = self.total_cases - self.passed_cases
        self.pass_rate = (self.passed_cases / self.total_cases * 100) if self.total_cases > 0 else 0
        
        self.avg_latency = self._calculate_avg_latency()
        self.total_tokens = self._calculate_total_tokens()
        self.estimated_cost = (self.total_tokens / 1_000_000) * 0.10 # $0.10 per 1M tokens baseline

    def _calculate_avg_latency(self) -> float:
        success_latencies = [c.raw_data.get("latency", 0) for c in self.cases if c.result_score == 1]
        if not success_latencies: return 0.0
        return sum(success_latencies) / len(success_latencies)

    def _calculate_total_tokens(self) -> int:
        total = 0
        for c in self.cases:
            # Check for usage metadata in raw data
            usage = c.raw_data.get("usage_metadata") or {}
            total += usage.get("total_tokens", 0)
            
            # Also check attempts for hidden token costs
            attempts = c.raw_data.get("generation_attempts") or []
            for att in attempts:
                att_usage = att.get("usage_metadata") or {}
                total += att_usage.get("total_tokens", 0)
        return total

    def get_failure_distribution(self) -> Dict[str, int]:
        """Returns a count of failures by category."""
        from collections import Counter
        return dict(Counter([c.primary_failure_category for c in self.cases if c.result_score == 0]))

def analyze_generator(generator_name: str, cases: List[CaseAnalysis]) -> GeneratorAnalysis:
    return GeneratorAnalysis(generator_name, cases)
