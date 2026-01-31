import os
import shutil
import subprocess
import json
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

        # Configuration via Environment Variables
        target_version = os.environ.get("TARGET_VERSION", "main")
        target_repo_url = os.environ.get("TARGET_REPO_URL", "Unknown Repository")
        index_url = os.environ.get("TARGET_INDEX_URL")

        # Resolve Index URL from Registry if not provided
        if not index_url:
            registry_path = root / "src" / "adk_knowledge_ext" / "registry.json"
            if registry_path.exists():
                try:
                    registry = json.loads(registry_path.read_text())
                    repo_map = registry.get(target_repo_url, {})
                    # Try specific version, fall back to main/default if needed (optional logic)
                    index_url = repo_map.get(target_version)
                    if index_url:
                        print(f"Build Hook: Resolved index URL from registry: {index_url}")
                except Exception as e:
                    print(f"Build Hook Warning: Failed to read registry: {e}")

        # 1. Download Index
        if index_url:
            index_path = indices_dir / f"index_{target_version}.yaml"
            print(f"Build Hook: Downloading index for {target_version} to {index_path} using {index_url}...")
            try:
                subprocess.run([
                    "curl", "-f", "-o", str(index_path), index_url
                ], check=True)
                print("Build Hook: Index bundling complete.")
            except Exception as e:
                print(f"Error downloading index: {e}")
                # We don't raise here to allow building without index (runtime fallback)
        else:
            print("Build Hook Warning: TARGET_INDEX_URL not set and not found in registry. Package will be built without bundled index.")

        # 2. Process Instructions Template
        template_path = root / "INSTRUCTIONS.template.md"
        output_path = data_dir / "INSTRUCTIONS.md"
        if template_path.exists():
            print(f"Build Hook: Generating INSTRUCTIONS.md for {target_repo_url}...")
            content = template_path.read_text()
            content = content.replace("{{TARGET_REPO_URL}}", target_repo_url)
            content = content.replace("{{TARGET_VERSION}}", target_version)
            output_path.write_text(content)
            print("Build Hook: Instructions bundling complete.")
        else:
            print("Build Hook Warning: INSTRUCTIONS.template.md not found.")
