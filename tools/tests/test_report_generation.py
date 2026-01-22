import pytest
import sys
from unittest.mock import MagicMock

# Mock dependencies before importing module under test
sys.modules["google.genai"] = MagicMock()
sys.modules["google.genai.types"] = MagicMock()
sys.modules["benchmarks.api_key_manager"] = MagicMock()

# Mocking internal dependencies to avoid import errors
sys.modules["benchmarks.data_models"] = MagicMock()
sys.modules["benchmarks.analysis"] = MagicMock()
sys.modules["tools.analysis.analyze_benchmark_run"] = MagicMock()
sys.modules["tools.cli.audit_failures"] = MagicMock()
sys.modules["tools.analysis.doc_generator"] = MagicMock()
sys.modules["tools.analysis.case_summarizer"] = MagicMock()
sys.modules["benchmarks.benchmark_candidates"] = MagicMock()

# Now import the class to test
from tools.cli.generate_benchmark_report import LogAnalyzer, HighLevelInsights, GeneratorAnalysisSection

class TestReportGeneration:
    def test_assemble_report_structure(self):
        """Tests that the report is assembled with correct header hierarchy."""
        analyzer = LogAnalyzer(model_name="test-model")
        
        # Mock data
        insights = HighLevelInsights(
            executive_summary="Exec Summary Content",
            cross_generator_comparison="Comparison Content",
            recommendations=["Rec 1", "Rec 2"]
        )
        
        gen_analysis = [
            GeneratorAnalysisSection(
                generator_name="Gen A",
                performance_summary="Perf A",
                docs_context_analysis="Docs A",
                tool_usage_analysis="Tools A",
                general_error_analysis="Errors A"
            )
        ]
        
        static_context = "### Gen A Internals\nDetails..."
        quantitative_context = "## 4. Quantitative Analysis\nTable..."
        suite_context = "\n\n## Benchmark Suites Overview\nTable..."
        forensic_context = "### Generator: Gen A\nFailures..."
        
        report = analyzer._assemble_report(
            insights=insights,
            generator_analyses=gen_analysis,
            static_context=static_context,
            quantitative_context=quantitative_context,
            suite_context=suite_context,
            forensic_context=forensic_context
        )
        
        # Assertions
        assert "# 📊 Benchmark Run Analysis" in report
        
        # Check Sections
        assert "## 1. Generator Internals & Configuration" in report
        assert "### Gen A Internals" in report # Content from static_context
        assert "# Generator Internals (Runtime Actualized)" not in report # Should NOT have H1
        
        assert "## 2. Executive Summary" in report
        assert "Exec Summary Content" in report
        
        assert "## 3. Benchmark Suites Overview" in report
        
        assert "## 4. Quantitative Analysis" in report
        
        assert "## 5. Generator Analysis" in report
        assert "### Gen A" in report
        
        assert "## 6. Cross-Generator Comparison" in report
        
        assert "## 7. Recommendations" in report
        
        assert "## 8. Forensic Analysis (Deep Dive)" in report
        
        assert "## 9. Report Generation Metadata" in report

    def test_assemble_report_filters_copyright(self):
        """Tests that copyright headers are filtered out of the forensic context."""
        analyzer = LogAnalyzer(model_name="test-model")
        
        # Mock data with copyright headers
        insights = HighLevelInsights(
            executive_summary="Exec",
            cross_generator_comparison="Comp",
            recommendations=[]
        )
        
        forensic_context = (
            "### Generator: Gen A\n"
            "# Copyright 2025 Google LLC\n"
                        "# Licensed under Apache\n"
            "Real content here.\n"
        )
        
        report = analyzer._assemble_report(
            insights=insights,
            generator_analyses=[],
            static_context="",
            quantitative_context="",
            suite_context="",
            forensic_context=forensic_context
        )
        
        assert "Real content here." in report
        assert "# Copyright 2025 Google LLC" not in report
        assert "# Licensed under Apache" not in report
