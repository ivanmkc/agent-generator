import sys
from pathlib import Path

# Add project root to sys.path for all tests
root = Path(__file__).resolve().parent

if str(root) not in sys.path:
    sys.path.insert(0, str(root))
