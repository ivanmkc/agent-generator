import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import json
from pathlib import Path

# Fix path
import sys
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from tools.cli.generate_benchmark_report import LogAnalyzer, HighLevelInsights, GeneratorAnalysisSection, ForensicInsight

class TestLogAnalyzer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.analyzer = LogAnalyzer(model_name="test-model")
        # Mock the client getter
        self.analyzer._get_client = MagicMock()
        self.mock_client = AsyncMock()
        self.analyzer._get_client.return_value = self.mock_client

    async def test_generate_content_returns_object(self):
        """Test that _generate_content returns a Pydantic object when schema is provided."""
        
        # Mock Response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "executive_summary": "Summary",
            "cross_generator_comparison": "Comparison",
            "recommendations": ["Rec1", "Rec2"]
        })
        mock_response.usage_metadata = None
        self.mock_client.aio.models.generate_content.return_value = mock_response

        # Call
        result = await self.analyzer._generate_content("prompt", schema=HighLevelInsights)
        
        # Verify
        self.assertIsInstance(result, HighLevelInsights)
        self.assertEqual(result.executive_summary, "Summary")

    async def test_generate_high_level_insights_fallback(self):
        """Test fallback when API fails."""
        # Mock failure
        self.mock_client.aio.models.generate_content.side_effect = Exception("API Error")
        
        result = await self.analyzer._generate_high_level_insights("summary", "stats")
        
        self.assertIsInstance(result, HighLevelInsights)
        self.assertEqual(result.executive_summary, "Failed to generate.")

    async def test_analyze_generator_fallback(self):
        """Test fallback for generator analysis."""
        self.mock_client.aio.models.generate_content.side_effect = Exception("API Error")
        
        result = await self.analyzer._analyze_generator("GenA", "logs")
        
        self.assertIsInstance(result, GeneratorAnalysisSection)
        self.assertEqual(result.performance_summary, "Analysis Failed.")

    async def test_map_reduce_logic(self):
        """Test the map-reduce flow (mocking the actual map/reduce methods)."""
        # This is a bit harder to test without mocking the private methods, 
        # but we can test the reducer method itself.
        
        mock_response = MagicMock()
        # Mock CaseSummary return
        mock_response.text = json.dumps({
            "benchmark_name": "bench_1",
            "failure_pattern": "Loop",
            "progression": "Stuck",
            "key_evidence": ["Ev1"]
        })
        self.mock_client.aio.models.generate_content.return_value = mock_response
        
        insights = [ForensicInsight(root_cause_category="C", explanation="E", evidence=[], dag_failure_point="DAG")]
        
        summary = await self.analyzer._reduce_case_insights("bench_1", insights)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary.failure_pattern, "Loop")

if __name__ == "__main__":
    unittest.main()
