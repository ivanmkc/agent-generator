import pytest
import os
import shutil
import subprocess
import yaml
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.cli.manage_registry import process_version_update, Registry, Repository, VersionInfo
from tools.cli.manage_registry import RANKED_TARGETS_YAML


@pytest.mark.asyncio
async def test_manage_registry_dynamic_cooccurrence_e2e(monkeypatch):
    """
    True integration test that creates local git repositories, 
    registers them in a dummy Registry WITHOUT namespaces, and processes an update to verify
    the end-to-end pipeline organically tracks external dependencies via dynamic discovery
    while explicitly filtering out standard library modules like 'sys' and 'os'.
    """
    with TemporaryDirectory() as root_tmp:
        root_path = Path(root_tmp)
        
        # 1. Create Main Dummy Repo
        main_repo_path = root_path / "main_repo"
        main_repo_path.mkdir()
        
        (main_repo_path / "main.py").write_text(
            "import dynamic_target\n"
            "import sys\n"
            "class MainApp:\n"
            "    def run(self): pass\n"
        )
        
        subprocess.run(["git", "init", "-b", "main"], cwd=main_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=main_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "init"], cwd=main_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "tag", "v1.0.0"], cwd=main_repo_path, check=True, capture_output=True)
        
        # 2. Create sample repo importing the targets across stdlib noise
        sample1_path = root_path / "sample_1"
        sample1_path.mkdir()
        (sample1_path / "usage.py").write_text(
            "import dynamic_target\n"
            "import os\n"
            "import external_pydantic\n"
        )
        
        (sample1_path / "usage2.py").write_text(
            "import dynamic_target\n"
            "import external_pydantic\n"
            "import sys\n"
            "import os\n"
        )
        
        subprocess.run(["git", "init", "-b", "main"], cwd=sample1_path, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=sample1_path, check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "init"], cwd=sample1_path, check=True, capture_output=True)
        
        # Bypass build_index generation step (since it requires a live Gemini API key)
        from tools.cli import manage_registry
        async def mock_build(*args, **kwargs): pass
        monkeypatch.setattr(manage_registry, "build_index", mock_build)
        
        # Also redirect the INDICES_DIR sandbox
        monkeypatch.setattr(manage_registry, "INDICES_DIR", root_path / "indices")
        
        registry = Registry(
            repositories={
                "test/repo": Repository(
                    repo_url=f"file://{main_repo_path.resolve()}",
                    description="Test E2E Dynamic Mode",
                    # NO namespaces here!
                    sample_repos=[
                        f"file://{sample1_path.resolve()}"
                    ],
                    versions={
                        "v1.0.0": VersionInfo(index_url="dummy")
                    }
                )
            }
        )
        
        # Run process
        await process_version_update("test/repo", "v1.0.0", force=True, registry=registry)
        
        # Verify the e2e results
        version_dir = root_path / "indices" / "test-repo" / "v1.0.0"
        
        cooccurrence_file = version_dir / "adk_cooccurrence.yaml"
        assert cooccurrence_file.exists(), f"Cooccurrence missing at {cooccurrence_file}"
        
        with open(cooccurrence_file, "r") as f:
            data = yaml.safe_load(f)
            
        assert len(data["meta"]["repo_paths"]) == 2
        # Verify dynamic discovery flag is set
        assert data["meta"]["is_dynamic"] is True
        
        # Extract all contexts and targets captured dynamically
        entities = set()
        for a in data["associations"]:
            entities.add(a["context"])
            entities.add(a["target"])
            
        # Ensure our third party targets were captured (appeared > 1 times)
        assert "dynamic_target" in entities
        assert "external_pydantic" in entities
        
        # CRITICAL: Ensure Python Standard Library modules were strictly ignored!
        assert "sys" not in entities, "stdlib 'sys' polluted the index!"
        assert "os" not in entities, "stdlib 'os' polluted the index!"
        
        ranked_yaml = version_dir / RANKED_TARGETS_YAML
        assert ranked_yaml.exists()
