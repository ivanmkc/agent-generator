import yaml
import tempfile
from pathlib import Path
from benchmarks.logger import YamlTraceLogger

def test_yaml_logger_robustness():
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = YamlTraceLogger(output_dir=tmp_dir, filename="test_trace.yaml")
        
        complex_data = {
            "bytes_val": b"some bytes",
            "set_val": {1, 2, 3},
            "nested": {"more_bytes": b"inner"}
        }
        
        # This should not raise TypeError
        logger._log_event("test_event", complex_data)
        
        # Verify content
        log_file = Path(tmp_dir) / "test_trace.yaml"
        assert log_file.exists()
        
        with open(log_file, "r") as f:
            # Load all documents from the YAML stream
            documents = list(yaml.safe_load_all(f))
            
        # First doc is run_start
        # Second doc is our event
        assert len(documents) >= 2
        data = documents[1]
        
        assert data["event_type"] == "test_event"
        # Bytes are handled by BytesEncoder/yaml representation? 
        # Actually in YamlTraceLogger we don't use BytesEncoder directly for yaml.dump, 
        # but yaml handles some things differently.
        # Wait, I didn't use BytesEncoder in YamlTraceLogger._log_event.
        # Let's check YamlTraceLogger implementation again.

if __name__ == "__main__":
    test_json_logger_robustness()
    print("Logging robustness test passed.")
