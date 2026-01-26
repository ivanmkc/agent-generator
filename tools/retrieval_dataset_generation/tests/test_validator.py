import unittest
import asyncio
from unittest.mock import MagicMock, patch
import math
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from tools.retrieval_dataset_generation.validate_data import DataValidator
from tools.retrieval_dataset_generation.lib import RetrievalCase, RetrievalContext, ValidatorConfig

class TestRetrievalValidator(unittest.TestCase):
    
    def setUp(self):
        self.config = ValidatorConfig(se_threshold=0.1)
        # Mock retrievers list (empty for unit tests of logic)
        self.validator = DataValidator("in.yaml", "out.yaml", [], config=self.config)

    def test_adjusted_se_safety_small_n(self):
        """
        Verify that for small N, even perfect results (p=1) do NOT converge.
        Safety Requirement: N must be > 10 for threshold 0.1.
        """
        # Case: 1 candidate. 
        fqns = ["doc1"]
        
        # Scenario: 5 trials. Doc1 present in all 5. Success in all 5.
        # n_in = 5, p_in = 1.0. n_out = 0 (irrelevant for this check's math on SE_in)
        # We need n_out > 0 for _check_convergence to return True/False instead of False immediately.
        # Let's say n_out = 5, p_out = 0.0.
        
        trials_in = {"doc1": 5}
        success_in = {"doc1": 5} # p_in = 1.0
        trials_out = {"doc1": 5}
        success_out = {"doc1": 0} # p_out = 0.0
        
        # Expected SE_in (Adjusted): 1/n_in = 1/5 = 0.2
        # Expected SE_out (Adjusted): 1/n_out = 1/5 = 0.2
        # Combined SE = sqrt(0.2^2 + 0.2^2) = 0.28
        # Threshold is 0.1. Should NOT converge.
        
        converged = self.validator._check_convergence(
            fqns, trials_in, success_in, trials_out, success_out, self.config.se_threshold
        )
        self.assertFalse(converged, "Should not converge with N=5 even with perfect separation.")

    def test_adjusted_se_convergence_large_n(self):
        """
        Verify that for large N, perfect results DO converge.
        """
        fqns = ["doc1"]
        # Scenario: 20 trials.
        # n=20 -> SE = 1/20 = 0.05. 
        # Combined SE = sqrt(0.05^2 + 0.05^2) = 0.07.
        # 0.07 < 0.1. Should converge.
        
        trials_in = {"doc1": 20}
        success_in = {"doc1": 20}
        trials_out = {"doc1": 20}
        success_out = {"doc1": 0}
        
        converged = self.validator._check_convergence(
            fqns, trials_in, success_in, trials_out, success_out, self.config.se_threshold
        )
        self.assertTrue(converged, "Should converge with N=20 and perfect separation.")

    def test_mixed_convergence_blocks_all(self):
        """
        Verify that if ANY candidate hasn't converged, the whole check returns False.
        """
        fqns = ["doc_stable", "doc_noisy"]
        
        # Doc Stable: N=20, p=1 (Converged)
        trials_in = {"doc_stable": 20, "doc_noisy": 20}
        success_in = {"doc_stable": 20, "doc_noisy": 10} # Noisy: p=0.5
        
        trials_out = {"doc_stable": 20, "doc_noisy": 20}
        success_out = {"doc_stable": 0, "doc_noisy": 10} # Noisy: p=0.5
        
        # Doc Noisy Stats:
        # p=0.5, n=20. SE = sqrt(0.5*0.5/20) = sqrt(0.0125) = 0.111
        # Combined SE = sqrt(0.11^2 + 0.11^2) = 0.157
        # 0.157 > 0.1. Should NOT converge.
        
        converged = self.validator._check_convergence(
            fqns, trials_in, success_in, trials_out, success_out, self.config.se_threshold
        )
        self.assertFalse(converged, "Should not converge if one candidate is noisy.")

class TestRetrievalIntegration(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.config = ValidatorConfig(
            adaptive_min_n=5, 
            adaptive_max_n=150, 
            se_threshold=0.2
        )
        self.validator = DataValidator("in.yaml", "out.yaml", [], config=self.config)
        
        # Setup specific mocks for async methods
        self.validator._generate_candidate_pool = MagicMock()
        self.validator._generate_answer_with_retry = MagicMock()
        
        # We need to mock the validation logic (e.g. _validate_api_understanding) 
        # to just return True/False based on our simulation rules.
        # Since _validate_api_understanding is called if generated_answer is not None, 
        # we can just make generated_answer return None to simulate failure, 
        # or return a dummy and mock the validation method.
        # Let's mock _validate_api_understanding.
        self.validator._validate_api_understanding = MagicMock()

    async def test_adaptive_convergence_simulation(self):
        """
        Simulate a run where:
        - 'magic_key': CAUSES success (100% when present, 0% when absent).
        - 'noise': IRRELEVANT (50% success always).
        
        Expectation:
        - 'magic_key' Delta P -> 1.0
        - 'noise' Delta P -> 0.0
        - Run stops when SE criteria met (likely around 20-30 trials).
        """
        case = RetrievalCase(
            id="test_case", query="q", source="api_understanding", metadata={},
            ground_truth={"answers": ["dummy"]}
        )
        
        # Candidates
        magic = RetrievalContext(fqn="magic_key", text="key", type="gold_mined")
        noise = RetrievalContext(fqn="noise", text="blah", type="random_noise")
        
        # Mock pool generation
        f = asyncio.Future()
        f.set_result([magic, noise])
        self.validator._generate_candidate_pool.return_value = f
        
        # Simulation Logic
        async def mock_generate(case, context):
            return "Generated Answer" # Always return something
            
        async def mock_validate(case, answer):
            # If magic_key text is in the context, probability is 1.0.
            # But wait, validate_case passes 'combined_text'. 
            # We can check if "magic_key" string is in context.
            # But the mock_generate receives context string.
            # We need to capture the context passed to generate.
            
            # Since generate calls are awaited, we can use side_effect on the mock.
            pass

        # We attach the logic to the validator's generate/validate flow.
        # Ideally we intercept the context in `validate_case` loop.
        # `generated_answer = await self._generate_answer_with_retry(case, combined_text)`
        
        async def generate_side_effect(case_obj, context_str):
            # Return a dummy object that holds the context for the validator to check
            ans = MagicMock()
            ans.raw_output = context_str # Pass context through
            return ans, "dummy_prompt"
            
        self.validator._generate_answer_with_retry.side_effect = generate_side_effect
        
        async def validate_side_effect(case_obj, answer_obj):
            context = answer_obj.raw_output
            
            has_magic = "[START_DOCUMENT: magic_key]" in context
            
            # Logic:
            # If Magic is present: 100% Success.
            # If Magic is absent: 0% Success.
            # Noise doesn't matter.
            
            return has_magic, None
            
        self.validator._validate_api_understanding.side_effect = validate_side_effect
        
        # Run Validation
        result = await self.validator.validate_case(case, mode="adaptive")
        
        # Verification
        trace = result.metadata['convergence_trace']
        print(f"\nSimulated Trials Run: {len(trace)}")
        
        magic_res = next(c for c in result.candidates if c.fqn == "magic_key")
        noise_res = next(c for c in result.candidates if c.fqn == "noise")
        
        print(f"Magic Delta P: {magic_res.metadata.delta_p}")
        print(f"Noise Delta P: {noise_res.metadata.delta_p}")
        
        # Assertions
        self.assertGreater(magic_res.metadata.delta_p, 0.9, "Magic key should have high impact")
        self.assertLess(abs(noise_res.metadata.delta_p), 0.2, "Noise should have low impact")
        
        # Safety Check: Should run at least 10 trials (as per our safety proof)
        self.assertGreater(len(trace), 10, "Should run at least 10 trials for safety")
        
        # Convergence Check: Should stop before max (150) if clean
        self.assertLess(len(trace), 150, "Should converge before max trials")

if __name__ == '__main__':
    unittest.main()
