import shutil
import subprocess
import yaml
import json
import re
from pathlib import Path
from typing import Dict

def sanitize_repo_name(url: str) -> str:
    """
    Converts a repo URL into a human-readable directory name.
    e.g. 'https://github.com/google/adk-python.git' -> 'google-adk-python'
    """
    # Remove protocol
    name = url.split("://")[-1]
    # Remove git extension
    if name.endswith(".git"):
        name = name[:-4]
    # Replace slashes and special chars with dashes
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name)
    return name.strip("-")

def bundle_indices(src_dir: Path, data_dir: Path) -> None:
    """
    Reads registry.yaml, downloads indices to data/indices/{repo_slug}/{version}.yaml,
    and generates manifest.json.
    """
    indices_dir = data_dir / "indices"
    
    # Clean previous build artifacts
    if data_dir.exists():
        shutil.rmtree(data_dir)
    indices_dir.mkdir(parents=True, exist_ok=True)

    manifest = {}
    registry_path = src_dir / "registry.yaml"
    
    if not registry_path.exists():
        print("Build Hook Warning: registry.yaml not found.")
        return

    print(f"Build Hook: Loading registry from {registry_path}...")
    try:
        registry = yaml.safe_load(registry_path.read_text())
        for repo_url, versions in registry.items():
            repo_slug = sanitize_repo_name(repo_url)
            
            # Create repo-specific directory
            repo_dir = indices_dir / repo_slug
            repo_dir.mkdir(parents=True, exist_ok=True)
            
            for ver, index_url in versions.items():
                filename = f"{ver}.yaml"
                index_path = repo_dir / filename
                
                # Store relative path in manifest
                manifest_entry = f"indices/{repo_slug}/{filename}"
                
                print(f"Build Hook: Downloading index for {repo_slug} ({ver}) to {manifest_entry}...")
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

    # Save Manifest
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Build Hook: Bundling complete. Manifest saved.")
