import json
import pytest
from pathlib import Path
from typing import Any, Optional
from benchmarks.answer_generators.gemini_cli_answer_generator import GeminiCliAnswerGenerator
from benchmarks.data_models import TraceLogEvent

DATA_DIR = Path(__file__).parent / "data" / "cli_outputs"

class MockGeminiCliAnswerGenerator(GeminiCliAnswerGenerator):
    def __init__(self, mcp_list_output_content: str, extensions_list_output_content: str):
        # Initialize parent with dummy values
        super().__init__(model_name="test-model", cli_path="gemini")
        self.mcp_list_output = mcp_list_output_content
        self.extensions_list_output = extensions_list_output_content

    async def _run_cli_command(self, cli_args: list[str], direct_command_parts: Optional[list[str]] = None) -> tuple[dict[str, Any], list[TraceLogEvent]]:
        cmd = direct_command_parts or cli_args
        stdout = ""
        # Check what command is being run
        if "mcp" in cmd and "list" in cmd:
            if "--output-format" in cmd and "json" in cmd:
                if self.mcp_list_output.strip() == "Configured MCP servers:\n(none)":
                    stdout = json.dumps({"servers": []})
                else:
                    stdout = json.dumps({"servers": [{"name": "context7"}]})
            else:
                stdout = self.mcp_list_output
        elif "extensions" in cmd and "list" in cmd:
            if "--output-format" in cmd and "json" in cmd:
                if self.extensions_list_output.strip() == "": # Assuming empty string means no extensions
                    stdout = json.dumps({"extensions": []})
                else:
                    stdout = json.dumps({"extensions": [{"id": "adk-docs-ext"}]})
            else:
                stdout = self.extensions_list_output
        
        # Return success (exit_code 0) to allow parsing to proceed
        return {"stdout": stdout, "stderr": "", "exit_code": 0}, []

@pytest.mark.asyncio
async def test_get_mcp_tools_parsing_mcp_only_real():
    mcp_output_content = (DATA_DIR / "mcp_list_connected_servers.txt").read_text()
    ext_output_content = "" # No extensions output for this specific test

    generator = MockGeminiCliAnswerGenerator(mcp_output_content, ext_output_content)
    tools = await generator.get_mcp_tools()
    
    print(f"DEBUG: Parsed tools (MCP only): {tools}")

    # Assertions for mcp_list_connected_servers.txt (should find context7)
    assert "context7" in tools
    assert "filesystem" not in tools  # Still not matched by current regex
    assert "other_server" not in tools
    
    # Extensions should NOT be here
    assert "adk-docs-ext" not in tools
    assert "codebase-investigator" not in tools


@pytest.mark.asyncio
async def test_get_mcp_tools_parsing_expected_success_split():
    mcp_output_content = (DATA_DIR / "mcp_list_connected_servers.txt").read_text()
    ext_output_content = (DATA_DIR / "extensions_list_valid_extensions_output.txt").read_text()
    
    generator = MockGeminiCliAnswerGenerator(mcp_output_content, ext_output_content)
    
    # 1. Test MCP Tools
    tools = await generator.get_mcp_tools()
    print(f"DEBUG: Parsed tools: {tools}")
    assert "context7" in tools
    
    # 2. Test Extensions
    extensions = await generator.get_gemini_cli_extensions()
    print(f"DEBUG: Parsed extensions: {extensions}")
    assert "adk-docs-ext" in extensions


@pytest.mark.asyncio
async def test_get_mcp_tools_parsing_empty():
    # Use mcp_list_empty.txt and empty string for extensions
    generator = MockGeminiCliAnswerGenerator( (DATA_DIR / "mcp_list_empty.txt").read_text(), "")
    
    tools = await generator.get_mcp_tools()
    extensions = await generator.get_gemini_cli_extensions()
    
    assert len(tools) == 0
    assert len(extensions) == 0
