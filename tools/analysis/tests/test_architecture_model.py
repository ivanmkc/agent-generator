import pytest
from tools.analysis.architecture_model import AgentArchitectureDocs, ToolDetail, ComponentDetail

def test_agent_architecture_docs_model():
    """Test that the Pydantic model correctly validates and serializes."""
    
    docs = AgentArchitectureDocs(
        core_philosophy="Test Philosophy",
        topology="Test Topology",
        key_tool_chain=["tool_a", "tool_b"],
        architecture_overview="Overview text",
        tool_chain_analysis=[
            ToolDetail(name="tool_a", purpose="Doing A", example="call_a()"),
            ToolDetail(name="tool_b", purpose="Doing B", example="call_b()")
        ],
        call_hierarchy_ascii="|-- A\n|-- B",
        call_flow_example="Step 1 -> Step 2",
        key_components=[
            ComponentDetail(name="CompA", responsibility="Resp A")
        ]
    )
    
    assert docs.core_philosophy == "Test Philosophy"
    assert len(docs.key_tool_chain) == 2
    assert docs.tool_chain_analysis[0].name == "tool_a"

def test_markdown_rendering():
    """Test the to_markdown method output format."""
    docs = AgentArchitectureDocs(
        core_philosophy="Philosophy",
        topology="Topology",
        key_tool_chain=["t1"],
        architecture_overview="Overview",
        tool_chain_analysis=[ToolDetail(name="t1", purpose="p1", example="e1")],
        call_hierarchy_ascii="ascii",
        call_flow_example="flow",
        key_components=[ComponentDetail(name="c1", responsibility="r1")]
    )
    
    md = docs.to_markdown()
    
    assert "### Concise Summary" in md
    assert "**Core Philosophy:** Philosophy" in md
    assert "`t1`" in md
    assert "### Extensive Architectural Breakdown" in md
    assert "**1. Architecture Overview**" in md
    assert "> Overview" in md
    assert "- **`t1`**: p1 (e.g., *e1*)" in md
