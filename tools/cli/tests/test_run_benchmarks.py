"""Test Run Benchmarks CLI script."""

import pytest
import shutil
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import the module under test
import tools.cli.run_benchmarks as run_benchmarks_module
from tools.cli.run_benchmarks import save_static_metadata, run_comparison, main

@pytest.fixture
def mock_logger():
    logger = MagicMock()
    # Mock context manager behavior for logger.section
    logger.section.return_value.__enter__.return_value = None
    return logger

@pytest.fixture
def temp_output_dir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    return d

def test_save_static_metadata_copies_docs(temp_output_dir):
    """
    Test that save_static_metadata correctly copies the architecture docs.
    This catches missing imports (like shutil) and path errors.
    """
    # Create a fake source doc
    fake_source = temp_output_dir / "fake_ARCHITECTURES.md"
    fake_source.write_text("Fake Architecture Docs")
    
    # Mock the generators
    mock_gen = MagicMock()
    mock_gen.name = "test-gen"
    mock_gen.model_name = "test-model"
    
    # Patch the path in the module to point to our fake source
    # We patch pathlib.Path to return our fake source when constructed with the specific string
    # This is brittle, so let's try to patch the specific variable usage logic or just set up the environment
    
    # Actually, simpler: The code does Path("benchmarks/answer_generators/ARCHITECTURES.md")
    # We can create that file relative to CWD if we change CWD, or we can mock Path.
    
    # Better approach: mocking shutil.copy to verify it's called, since we can't easily control the source path hardcoded in the function without refactoring.
    # BUT, the bug was NameError: name 'shutil' is not defined.
    # Just calling the function successfully is enough to prove the import is there.
    
    with patch("tools.cli.run_benchmarks.shutil.copy") as mock_copy:
        with patch("tools.cli.run_benchmarks.Path.exists", return_value=True):
             save_static_metadata(temp_output_dir, [mock_gen], ["suite1"])
             
             mock_copy.assert_called()

@pytest.mark.asyncio
async def test_run_comparison_filtering(mock_logger, temp_output_dir):
    """
    Test that run_comparison filters generators and suites correctly.
    """
    
    # Mock CANDIDATE_GENERATORS
    gen1 = MagicMock()
    gen1.name = "Gen1"
    gen1.model_name = "ModelA"
    gen1.setup = AsyncMock()
    gen1.teardown = AsyncMock()
    
    gen2 = MagicMock()
    gen2.name = "Gen2"
    gen2.model_name = "ModelB"
    gen2.setup = AsyncMock()
    gen2.teardown = AsyncMock()
    
    with patch("tools.cli.run_benchmarks.CANDIDATE_GENERATORS", [gen1, gen2]):
        with patch("tools.cli.run_benchmarks.benchmark_orchestrator.run_benchmarks", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = []
            
            # Filter by generator name
            await run_comparison(
                logger=mock_logger,
                run_output_dir=temp_output_dir,
                selected_generator_filter="Gen1"
            )
            
            # Should have run only Gen1
            assert mock_run.call_count == 1
            args, _ = mock_run.call_args
            # generators is the second arg (index 1) if positional, or keyword arg
            # The signature is (benchmark_suites, answer_generators, ...)
            # Let's check call_args kwargs
            kwargs = mock_run.call_args.kwargs
            generators = kwargs.get("answer_generators")
            assert len(generators) == 1
            assert generators[0].name == "Gen1"

@pytest.mark.asyncio
async def test_main_arg_parsing(tmp_path):
    """Test that main() correctly parses args and calls run_comparison."""
    
    # Mock sys.argv
    with patch.object(sys, 'argv', ['run_benchmarks.py', '--suite-filter', 'debug']):
        # Mock environment var to avoid date-based directory
        with patch.dict(os.environ, {"BENCHMARK_OUTPUT_DIR": str(tmp_path)}):
            # Mock run_comparison to avoid actual execution
            with patch("tools.cli.run_benchmarks.run_comparison", new_callable=AsyncMock) as mock_run_comp:
                mock_run_comp.return_value = []
                
                # Mock logging setup
                with patch("tools.cli.run_benchmarks.YamlTraceLogger"), \
                     patch("tools.cli.run_benchmarks.ConsoleBenchmarkLogger"):
                    
                    await main()
                    
                    mock_run_comp.assert_called_once()
                    call_kwargs = mock_run_comp.call_args.kwargs
                    assert call_kwargs['selected_suite'] == 'debug'

