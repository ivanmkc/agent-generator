import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from click.testing import CliRunner
import sys
import re
from pathlib import Path

# Ensure import works
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from adk_knowledge_ext import manage_mcp

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_mcp_client():
    """Mocks the MCP client context managers and session."""
    with (
        patch("adk_knowledge_ext.manage_mcp.stdio_client") as mock_stdio,
        patch("adk_knowledge_ext.manage_mcp.ClientSession") as mock_session_cls
    ):
        
        # Setup the async context manager for stdio_client
        mock_read = MagicMock()
        mock_write = MagicMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
        mock_stdio.return_value.__aexit__.return_value = None
        
        # Setup the async context manager for ClientSession
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session_cls.return_value.__aexit__.return_value = None
        
        yield mock_session

def create_tool_result(text, is_error=False):
    """Helper to create a mock tool result object."""
    content_obj = MagicMock()
    content_obj.text = text
    result = MagicMock()
    result.content = [content_obj]
    result.isError = is_error
    return result

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {})
def test_debug_inspect_symbol_success_with_error_word(mock_mcp_client, runner):
    """
    Scenario: Success with "False Positive" Text
    Verifies that inspect_symbol is marked as OK even if the returned docstring 
    contains the word "Error" or "not found", provided it doesn't match a failure pattern.
    This prevents false positives when documentation describes error conditions.
    """
    # 1. List Tools (Success)
    t1 = MagicMock(); t1.name = "list_modules"
    t2 = MagicMock(); t2.name = "search_knowledge"
    t3 = MagicMock(); t3.name = "inspect_symbol"
    
    tools_result = MagicMock()
    tools_result.tools = [t1, t2, t3]
    mock_mcp_client.list_tools.return_value = tools_result
    
    # 2. Mock responses for the sequence of calls
    
    docstring_with_error = """
    rank: 1
    id: google.adk.runners.InMemoryRunner
    docstring: "Raises: ValueError: If the session is not found."
    """
    
    mock_mcp_client.call_tool.side_effect = [
        create_tool_result("[1] CLASS: google.adk.runners.InMemoryRunner"), # list_modules
        create_tool_result("Found some stuff"), # search_knowledge
        create_tool_result(docstring_with_error) # inspect_symbol
    ]
    
    result = runner.invoke(manage_mcp.debug)
    clean_output = strip_ansi(result.output)
    
    # We expect "inspect_symbol" to NOT show "Failed"
    # It should show "OK"
    assert "✅ OK" in clean_output
    # Specifically for the inspect step
    # We can check that we don't see "Output (Error)" which is printed on failure
    assert "Output (Error)" not in clean_output

@patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {})
def test_debug_inspect_symbol_real_failure(mock_mcp_client, runner):
    """
    Scenario: Logical Failure ("Symbol Not Found")
    Verifies that inspect_symbol is marked as Failed when the server returns the specific 
    'Symbol ... not found' message. This is technically a success at the MCP protocol level 
    but a failure for our diagnostic.
    """
    # 1. List Tools
    t1 = MagicMock(); t1.name = "list_modules"
    t2 = MagicMock(); t2.name = "search_knowledge"
    t3 = MagicMock(); t3.name = "inspect_symbol"
    
    tools_result = MagicMock()
    tools_result.tools = [t1, t2, t3]
    mock_mcp_client.list_tools.return_value = tools_result
    
    # 2. Mock responses
    mock_mcp_client.call_tool.side_effect = [
        create_tool_result("[1] CLASS: google.adk.runners.InMemoryRunner"), 
        create_tool_result("Found stuff"), 
        create_tool_result("Symbol 'google.adk.runners.InMemoryRunner' not found in index.") 
    ]
    
    result = runner.invoke(manage_mcp.debug)
    clean_output = strip_ansi(result.output)
    
    # Should contain failure indicator
    assert "❌ Failed" in clean_output
    assert "Output (Error)" in clean_output

@patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {})
def test_debug_inspect_symbol_generic_error(mock_mcp_client, runner):
    """
    Scenario: Explicit Error Prefix
    Verifies that inspect_symbol is marked as Failed if it returns a string starting with "Error: ...".
    This catches generic errors returned as text.
    """
    t1 = MagicMock(); t1.name = "list_modules"
    t2 = MagicMock(); t2.name = "search_knowledge"
    t3 = MagicMock(); t3.name = "inspect_symbol"
    
    tools_result = MagicMock()
    tools_result.tools = [t1, t2, t3]
    mock_mcp_client.list_tools.return_value = tools_result
    
    mock_mcp_client.call_tool.side_effect = [
        create_tool_result("[1] CLASS: google.adk.runners.InMemoryRunner"), 
        create_tool_result("Found stuff"), 
        create_tool_result("Error: Something went wrong.") 
    ]
    
    result = runner.invoke(manage_mcp.debug)
    clean_output = strip_ansi(result.output)
    
    assert "❌ Failed" in clean_output
    assert "Output (Error)" in clean_output

@patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {})
def test_debug_inspect_symbol_is_error(mock_mcp_client, runner):
    """
    Scenario: Protocol-Level Error (isError=True)
    Verifies that if the MCP result object explicitly flags an error (`result.isError`), 
    the diagnostic correctly reports Failed, even if the response text is benign or ambiguous.
    """
    t1 = MagicMock(); t1.name = "list_modules"
    t2 = MagicMock(); t2.name = "search_knowledge"
    t3 = MagicMock(); t3.name = "inspect_symbol"
    
    tools_result = MagicMock()
    tools_result.tools = [t1, t2, t3]
    mock_mcp_client.list_tools.return_value = tools_result
    
    mock_mcp_client.call_tool.side_effect = [
        create_tool_result("[1] CLASS: google.adk.runners.InMemoryRunner"), 
        create_tool_result("Found stuff"), 
        create_tool_result("Some unexpected error occurred internally", is_error=True) 
    ]
    
    result = runner.invoke(manage_mcp.debug)
    clean_output = strip_ansi(result.output)
    
    assert "❌ Failed" in clean_output
    assert "Output (Error)" in clean_output