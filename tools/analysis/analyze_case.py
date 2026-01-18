from typing import List, Dict, Any
from tools.analysis.analyze_attempt import analyze_attempt, AttemptAnalysis

# Error Classifier Configuration
ERROR_PATTERNS = [
    (r"JSONDecodeError", "Malformed JSON"),
    (r"AttributeError.*has no attribute", "Interface Violation"),
    (r"AttributeError", "Code Logic Error"),
    (r"SyntaxError", "Syntax Error"),
    (r"Validation Failed", "Output Validation Error"),
    (r"Expected '.*', but got", "Incorrect Answer (MC)"),
    (r"Quota Limit", "Infrastructure Error"),
    (r"429 Resource Exhausted", "Infrastructure Error"),
]

def classify_error(error_msg):
    if not error_msg: return "Unknown"
    for pattern, category in ERROR_PATTERNS:
        import re
        if re.search(pattern, str(error_msg), re.IGNORECASE):
            return category
    return "Generic Failure"

class CaseAnalysis:
    def __init__(self, case_data: Dict[str, Any]):
        self.raw_data = case_data
        self.benchmark_name = case_data.get("benchmark_name")
        self.suite = case_data.get("suite", "unknown")
        self.generator = case_data.get("answer_generator", "unknown")
        self.result_score = case_data.get("result", 0) # 1 or 0
        self.final_validation_error = case_data.get("validation_error")
        
        self.attempts: List[AttemptAnalysis] = []
        self._analyze_attempts()

    def _analyze_attempts(self):
        raw_attempts = self.raw_data.get("generation_attempts") or []
        
        # Backward compatibility for flat logs (no attempts array)
        if not raw_attempts and self.raw_data.get("trace_logs"):
            # Construct a synthetic attempt from the top-level trace
            raw_attempts = [{
                "attempt_number": 1,
                "status": "failed" if self.result_score == 0 else "success",
                "trace_logs": self.raw_data.get("trace_logs"),
                "error_message": self.final_validation_error
            }]

        for att_data in raw_attempts:
            # Inject top-level truth/answer if missing in attempt
            if "ground_truth" not in att_data:
                att_data["ground_truth"] = self.raw_data.get("ground_truth")
            if "answer" not in att_data:
                att_data["answer"] = self.raw_data.get("answer")
                
            self.attempts.append(analyze_attempt(att_data))

    @property
    def question_summary(self) -> str:
        """Returns a concise summary of the benchmark question."""
        if not self.attempts or not self.attempts[0].question:
            return "No question context available."
            
        full_q = self.attempts[0].question
        
        # remove boilerplate
        patterns = [
            r"You are an expert.*?framework\.",
            r"Answer the following.*?question\.",
            r"Return the result as a JSON.*",
            r"Task Type:.*"
        ]
        
        clean_q = full_q
        for p in patterns:
            import re
            clean_q = re.sub(p, "", clean_q, flags=re.IGNORECASE | re.DOTALL)
            
        # Clean whitespace
        clean_q = " ".join(clean_q.split()).strip()
        
        # Truncate
        if len(clean_q) > 150:
            return clean_q[:147] + "..."
            
        return clean_q

    @property
    def primary_failure_category(self) -> str:
        """Classifies the failure based on the final validation error."""
        if self.result_score == 1:
            return "None (Passed)"
        return classify_error(self.final_validation_error)

    @property
    def has_critical_heuristic_failure(self) -> bool:
        """Returns True if any attempt exhibited a critical architecture bug."""
        return any(a.has_sanitizer_hallucination or a.loop_early_exit for a in self.attempts)

def analyze_case(case_data: Dict[str, Any]) -> CaseAnalysis:
    return CaseAnalysis(case_data)
