import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from tools.analysis.generate_architecture_docs import GeneratorDocManager
from tools.analysis.architecture_model import AgentArchitectureDocs

# Sample MD content
SAMPLE_MD = """# Answer Generator Architectures

## existing-agent

### Core Philosophy
Existing philosophy.

### Architecture Overview
Existing overview.
"""

@pytest.fixture
def temp_architectures_md(tmp_path):
    """Creates a temporary ARCHITECTURES.md file."""
    p = tmp_path / "ARCHITECTURES.md"
    p.write_text(SAMPLE_MD)
    return p

@pytest.mark.asyncio
async def test_get_description_existing(temp_architectures_md):
    """Test retrieving documentation for an existing agent."""
    manager = GeneratorDocManager(architectures_path=temp_architectures_md)
    
    # "existing-agent" is in the mock MD
    desc = await manager.get_description("existing-agent", None, "mock-model")
    
    assert "Architecture Details (from ARCHITECTURES.md)" in desc
    assert "Existing philosophy" in desc

@pytest.mark.asyncio
async def test_get_description_missing_generates_and_appends(temp_architectures_md):
    """Test that missing documentation triggers generation and is saved."""
    
    # Mock the LLM generation return value
    mock_docs = AgentArchitectureDocs(
        core_philosophy="New philosophy",
        topology="New topology",
        key_tool_chain=["tool1"],
        architecture_overview="New overview",
        tool_chain_analysis=[],
        call_hierarchy_ascii="graph",
        call_flow_example="flow",
        key_components=[]
    )
    
    manager = GeneratorDocManager(architectures_path=temp_architectures_md)
    
    # Mock _generate_docs to avoid API calls
    with patch.object(manager, '_generate_docs', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_docs
        
        # "new-agent" is NOT in the mock MD
        desc = await manager.get_description("new-agent", None, "mock-model")
        
        # Verify it returned the generated content
        assert "Architecture Details (LLM Generated & Saved)" in desc
        assert "New philosophy" in desc
        
        # Verify it was appended to the file
        content = temp_architectures_md.read_text()
        assert "## new-agent" in content
        assert "New philosophy" in content
        assert "New overview" in content

@pytest.mark.asyncio
async def test_key_normalization(temp_architectures_md):
    """Test that keys with prefixes (like in run_metadata.json) are normalized."""
    manager = GeneratorDocManager(architectures_path=temp_architectures_md)
    
    # "GeminiCliPodman: existing-agent" should match "existing-agent" header
    desc = await manager.get_description("GeminiCliPodman: existing-agent", None, "mock-model")
    
    assert "Architecture Details (from ARCHITECTURES.md)" in desc
