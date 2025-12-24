import json
import tempfile
from pathlib import Path
from benchmarks.logger import JsonTraceLogger

def test_json_logger_robustness():
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = JsonTraceLogger(output_dir=tmp_dir, filename="test_trace.jsonl")
        
        complex_data = {
            "bytes_val": b"some bytes",
            "set_val": {1, 2, 3},
            "nested": {"more_bytes": b"inner"}
        }
        
        # This should not raise TypeError
        logger._log_event("test_event", complex_data)
        
        # Verify content
        log_file = Path(tmp_dir) / "test_trace.jsonl"
        assert log_file.exists()
        
        with open(log_file, "r") as f:
            lines = f.readlines()
            
        # First line is run_start
        # Second line is our event
        assert len(lines) >= 2
        event_line = lines[1]
        data = json.loads(event_line)
        
        assert data["event_type"] == "test_event"
        # Bytes are serialized to repr string by BytesEncoder
        assert data["data"]["bytes_val"] == "b'some bytes'" 
        # Sets are serialized to lists by BytesEncoder
        assert set(data["data"]["set_val"]) == {1, 2, 3}

if __name__ == "__main__":
    test_json_logger_robustness()
    print("Logging robustness test passed.")
