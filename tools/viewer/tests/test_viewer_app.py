from streamlit.testing.v1 import AppTest
import sys
from pathlib import Path

def test_viewer_app_smoke():
    """Smoke test to ensure the Streamlit app loads without syntax or import errors."""
    # Resolve path to the viewer script
    script_path = Path(__file__).parents[1] / "view_benchmarks.py"
    
    # Initialize the AppTest
    at = AppTest.from_file(str(script_path))
    
    # Run the app
    at.run()
    
    # Check if there are any exceptions
    assert not at.exception, f"App failed to launch: {at.exception}"
    
    # Basic check to ensure title is present (verifies basic rendering)
    # The title in view_benchmarks.py is "📊 ADK Benchmark Viewer"
    assert len(at.title) > 0
    assert "Benchmark Viewer" in at.title[0].value
