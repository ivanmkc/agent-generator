import os
import shutil
import subprocess
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root)
        data_dir = root / "src" / "adk_knowledge_ext" / "data"
        indices_dir = data_dir / "indices"
        
        # Clean previous build artifacts
        if data_dir.exists():
            shutil.rmtree(data_dir)
        indices_dir.mkdir(parents=True, exist_ok=True)

        # Map of version -> url
        default_base_url = "https://raw.githubusercontent.com/ivanmkc/agent-generator/main/benchmarks/generator/benchmark_generator/data/ranked_targets.yaml"
        # Allow override for testing/local dev
        base_url = os.environ.get("ADK_INDEX_URL", default_base_url)

        versions = {
            "v1.20.0": base_url
        }

        for ver, url in versions.items():
            index_path = indices_dir / f"ranked_targets_{ver}.yaml"
            print(f"Build Hook: Downloading index for {ver} to {index_path} using {url}...")
            try:
                subprocess.run([
                    "curl", "-f", "-o", str(index_path), url
                ], check=True)
            except Exception as e:
                print(f"Error downloading index for {ver}: {e}")
                # We might want to fail the build, or just warn
                raise
            
        print("Build Hook: Indices bundling complete.")
