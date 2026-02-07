
import pytest
import sys
import yaml
import asyncio
from pathlib import Path

from tools.knowledge.target_ranker.ranker import TargetRanker

@pytest.mark.asyncio
async def test_ranker_bfs_discovery_public_api(tmp_path):
    """
    Verifies that TargetRanker:
    1. Discovers external dependencies in `dependency_root` via BFS.
    2. Respects the Public API constraint (follows signatures/bases, ignores function bodies).
    3. Does not index internal implementation details.
    """
    
    # Setup Directories
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    
    # --- 1. Create Repository (Seed) ---
    # repo/main.py uses library.Core explicitly in a signature
    (repo_dir / "main.py").write_text(
        "import library\n"
        "def main(c: library.Core):\n"
        "    pass\n"
    )
    
    # --- 2. Create Dependencies ---
    lib_dir = deps_dir / "library"
    lib_dir.mkdir()
    
    # library/__init__.py
    (lib_dir / "__init__.py").write_text(
        "from .core import Core\n"
    )
    
    # library/core.py
    # - Inherits from public_sig.Base (Public API linkage)
    # - Uses hidden_impl.Secret inside a method body (Implementation Detail - Should be IGNORED)
    (lib_dir / "core.py").write_text(
        "import public_sig\n"
        "import hidden_impl\n"
        "\n"
        "class Core(public_sig.Base):\n"
        "    def method(self):\n"
        "        # Implementation detail usage\n"
        "        s = hidden_impl.Secret()\n"
    )
    
    # public_sig.py (Should be Discovered)
    (deps_dir / "public_sig.py").write_text(
        "class Base:\n"
        "    pass\n"
    )
    
    # hidden_impl.py (Should be Ignored)
    (deps_dir / "hidden_impl.py").write_text(
        "class Secret:\n"
        "    pass\n"
    )

    # --- Verification: Public Signature (Type Hint) ---
    # repo/tc02.py
    (repo_dir / "tc02.py").write_text(
        "import ext_tc02\n"
        "def connect(config: ext_tc02.Config) -> None:\n"
        "    pass\n"
    )
    (deps_dir / "ext_tc02.py").write_text(
        "class Config: pass\n"
    )

    # --- Verification: Out of Scope (Stdlib Exclusion) ---
    # repo/tc04.py
    (repo_dir / "tc04.py").write_text(
        "import datetime\n"
        "def get_time(dt: datetime.datetime):\n"
        "    pass\n"
    )
    # check that datetime is NOT in deps_dir (it isn't by default)

    # --- Verification: Module Level Annotation ---
    # repo/tc05.py
    # We treat module-level annotations as public for safety
    (repo_dir / "tc05.py").write_text(
        "import ext_tc05\n"
        "_private_attr: ext_tc05.InternalType = None\n"
    )
    (deps_dir / "ext_tc05.py").write_text(
        "class InternalType: pass\n"
    )

    # --- Verification: Public Decorator ---
    # repo/tc06.py
    (repo_dir / "tc06.py").write_text(
        "import ext_tc06\n"
        "@ext_tc06.register\n"
        "def my_func(): ...\n"
    )
    # Ensure decorator function is long enough to bypass scanner's 3-line heuristic
    (deps_dir / "ext_tc06.py").write_text(
        "def register(f):\n"
        "    '''Registration decorator.'''\n"
        "    # Some logic to make it longer\n"
        "    return f\n"
    )
    
    # Output paths
    out_yaml = tmp_path / "ranked_targets.yaml"
    out_md = tmp_path / "ranked_targets.md"
    
    # --- 3. Run Ranker ---
    ranker = TargetRanker(
        repo_path=str(repo_dir),
        dependency_root=str(deps_dir),
        namespace=None  # Allow scanning all files in repo_dir (e.g. main.py)
    )
    
    await ranker.generate(output_yaml_path=str(out_yaml), output_md_path=str(out_md))
    
    # --- 4. Verify Results ---
    with open(out_yaml) as f:
        data = yaml.safe_load(f)
        
    ids = {item["id"] for item in data}
    print(f"Discovered IDs: {ids}")
    
    # Assertions
    assert "library.core.Core" in ids, "Core class should be discovered via import in main.py"
    assert "public_sig.Base" in ids, "Base class should be discovered via inheritance (Public API)"
    
    assert "hidden_impl.Secret" not in ids, "Secret class (implementation detail) should NOT be discovered"
    assert "hidden_impl" not in ids, "hidden_impl module should NOT be discovered"

    # Verification: Public Signature (Type Hint)
    assert "ext_tc02.Config" in ids, "Config should be discovered via type hint"
    
    # Verification: Out of Scope (Stdlib Exclusion)
    # datetime is stdlib, so it shouldn't be in our ranked targets unless we index stdlib (which we don't here as dependency_root is tmp_deps)
    assert not any("datetime" in i for i in ids), "datetime (stdlib) should not be discovered (out of scope)"

    # Verification: Module Level Annotation
    assert "ext_tc05.InternalType" in ids, "Module level annotation should be discovered"

    # Verification: Public Decorator
    # Decorator verification: verify the decorator function itself is indexed
    assert "ext_tc06.register" in ids or "ext_tc06" in ids, "Decorator should be discovered"

if __name__ == "__main__":
    # Manually run if executed as script
    asyncio.run(test_ranker_bfs_discovery_public_api(Path("./test_tmp")))
