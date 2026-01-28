import sys
from pathlib import Path

# Add project root and search extension to sys.path for all tests
root = Path(__file__).resolve().parent
ext_src = root / "tools/adk_knowledge_ext/src"

if str(root) not in sys.path:
    sys.path.insert(0, str(root))
if str(ext_src) not in sys.path:
    sys.path.insert(0, str(ext_src))
