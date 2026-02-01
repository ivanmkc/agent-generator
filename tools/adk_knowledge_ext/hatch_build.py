import os
import shutil
import subprocess
import yaml
import json
import hashlib
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root)
        src_dir = root / "src" / "adk_knowledge_ext"
        data_dir = src_dir / "data"
        indices_dir = data_dir / "indices"
        
        # Clean previous build artifacts
        if data_dir.exists():
            shutil.rmtree(data_dir)
        indices_dir.mkdir(parents=True, exist_ok=True)

        manifest = {}
        registry_path = src_dir / "registry.yaml"
        
        # 1. Bundle indices from Registry
        if registry_path.exists():
            print(f"Build Hook: Loading registry from {registry_path}...")
            try:
                registry = yaml.safe_load(registry_path.read_text())
                for repo_url, versions in registry.items():
                    repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
                    # Create repo-specific directory
                    repo_dir = indices_dir / repo_hash
                    repo_dir.mkdir(parents=True, exist_ok=True)
                    
                    for ver, index_url in versions.items():
                        filename = f"{ver}.yaml"
                        index_path = repo_dir / filename
                        
                        # Store relative path in manifest (e.g., "abcdef12/v1.0.0.yaml")
                        manifest_entry = f"{repo_hash}/{filename}"
                        
                        print(f"Build Hook: Downloading index for {repo_url} ({ver}) to {manifest_entry}...")
                        try:
                            subprocess.run(["curl", "-f", "-L", "-o", str(index_path), index_url], check=True)
                            
                            # Update manifest
                            if repo_url not in manifest:
                                manifest[repo_url] = {}
                            manifest[repo_url][ver] = manifest_entry
                            
                        except subprocess.CalledProcessError as e:
                            print(f"Build Hook Warning: Failed to download {index_url}: {e}")
            except Exception as e:
                print(f"Build Hook Warning: Failed to process registry: {e}")

        # 2. Bundle specific index via Env Var (Override/Addition)
        target_version = os.environ.get("TARGET_VERSION", "main")
        target_repo_url = os.environ.get("TARGET_REPO_URL")
        target_index_url = os.environ.get("TARGET_INDEX_URL")

        if target_index_url:
            # If explicitly requested, we save it as a specific filename that server.py looks for by default 
            # OR we add it to the manifest. Let's add to manifest to be consistent.
            # But if TARGET_REPO_URL is missing, we can't key it properly.
            # Legacy fallback: save as index_TARGET_VERSION.yaml for backward compat if needed, 
            # but ideally we just use the manifest.
            
            # For now, if provided manually, we trust the user knows what they are doing.
            # We will save it as 'custom_main.yaml' or similar if we can't identify repo.
            pass # The server logic will handle specific overrides, but for bundling, we focus on registry.

        # Save Manifest
        (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print("Build Hook: Bundling complete. Manifest saved.")

        # 3. Process Instructions Template (Generic or Specific)
        # If we are bundling multiple, we can't pre-fill the specific URL in INSTRUCTIONS.md
        # The server should handle template filling at runtime or we provide a generic one.
        # However, for backward compatibility, if env vars ARE present, we generate one.
        template_path = root / "INSTRUCTIONS.template.md"
        output_path = data_dir / "INSTRUCTIONS.md"
        if template_path.exists():
            content = template_path.read_text()
            # Defaults for generic bundle
            content = content.replace("{{TARGET_REPO_URL}}", target_repo_url or "(Determined at Runtime)")
            content = content.replace("{{TARGET_VERSION}}", target_version)
            output_path.write_text(content)
        else:
            print("Build Hook Warning: INSTRUCTIONS.template.md not found.")