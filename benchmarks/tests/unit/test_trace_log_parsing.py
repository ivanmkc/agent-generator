import pytest
from pathlib import Path
from benchmarks.utils import parse_cli_stream_json_output
from benchmarks.data_models import TraceLogEvent

DATA_DIR = Path(__file__).parent / "data" / "cli_outputs"

def test_parse_cli_stream_json_output_real():
    stdout_content = (DATA_DIR / "trace_stream_json_output.txt").read_text()
    
    response_dict, logs = parse_cli_stream_json_output(stdout_content)
    
    print(f"DEBUG: Parsed logs from stdout: {[log.model_dump() for log in logs]}")
    
    assert logs, "Should have parsed some logs"
    
    # Verify specific log types found
    log_types = [log.type for log in logs]
    assert "init" in log_types
    assert "message" in log_types
    assert "system_result" in log_types # 'result' event maps to 'system_result' type in TraceLogEvent usually
    
    # Verify content of the 'message' log (assistant response about deprecation)
    assistant_msgs = [log for log in logs if log.role == "assistant"]
    assert any("deprecated" in log.content for log in assistant_msgs)

def test_trace_log_integration_mock():
    # This mimics how GeminiCliAnswerGenerator combines stdout and stderr
    stdout_content = (DATA_DIR / "trace_stream_json_output.txt").read_text()
    stderr_content = (DATA_DIR / "trace_stderr_api_error.txt").read_text()
    
    # 1. Parse stderr first (as done in generator)
    logs = []
    for line in stderr_content.splitlines():
        if line.strip():
            logs.append(TraceLogEvent(type="CLI_STDERR", source="podman", content=line.strip()))
            
    # 2. Parse stdout
    _, parsed_logs = parse_cli_stream_json_output(stdout_content)
    logs.extend(parsed_logs)
    
    # Verify mixed logs
    assert any(log.type == "CLI_STDERR" for log in logs)
    assert any(log.type == "init" for log in logs)
    
    # Check for specific stderr content
    assert any("Error generating content" in log.content for log in logs if log.type == "CLI_STDERR")
