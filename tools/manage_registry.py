#!/usr/bin/env python3
"""
Management tool for the Codebase Knowledge Registry.
Automates index generation, validation, and registry updates.
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.target_ranker.ranker import TargetRanker

REGISTRY_PATH = project_root / "tools/adk_knowledge_ext/src/adk_knowledge_ext/registry.yaml"
INDICES_DIR = project_root / "tools/adk_knowledge_ext/src/adk_knowledge_ext/data/indices"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("manage_registry")

def load_registry() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"repositories": {}}
    with open(REGISTRY_PATH, "r") as f:
        return yaml.safe_load(f) or {"repositories": {}}

def save_registry(data: Dict[str, Any]):
    with open(REGISTRY_PATH, "w") as f:
        yaml.dump(data, f, sort_keys=False, width=1000)

class RegistryManager:
    def __init__(self):
        self.registry = load_registry()

    def get_repo_info(self, repo_id: str) -> Optional[Dict[str, Any]]:
        return self.registry.get("repositories", {}).get(repo_id)

    async def check_updates(self, repo_id: str = None):
        """Checks for new git tags that are not in the registry."""
        repos = self.registry.get("repositories", {})
        target_repos = [repo_id] if repo_id else repos.keys()

        for rid in target_repos:
            info = repos.get(rid)
            if not info:
                logger.error(f"Repository {rid} not found.")
                continue

            repo_url = info["repo_url"]
            logger.info(f"Checking updates for {rid} ({repo_url})...")
            
            try:
                result = subprocess.run(
                    ["git", "ls-remote", "--tags", repo_url],
                    capture_output=True, text=True, check=True
                )
                tags = []
                for line in result.stdout.splitlines():
                    if "refs/tags/" in line:
                        tag = line.split("refs/tags/")[-1].replace("^{}", "")
                        if tag not in tags:
                            tags.append(tag)
                
                existing_versions = info.get("versions", {}).keys()
                new_tags = [t for t in tags if t not in existing_versions]
                
                if new_tags:
                    logger.info(f"Found {len(new_tags)} new tags for {rid}: {', '.join(new_tags)}")
                else:
                    logger.info(f"No new tags found for {rid}.")
            except Exception as e:
                logger.error(f"Failed to check updates for {rid}: {e}")

    async def add_version(self, repo_id: str, version: str, golden_symbols: List[str] = None):
        """Clones, indexes, validates, and adds a new version to the registry."""
        info = self.get_repo_info(repo_id)
        if not info:
            logger.error(f"Repository {repo_id} not found in registry. Use 'add-repo' first.")
            return

        repo_url = info["repo_url"]
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            repo_path = tmp_path / "repo"
            
            logger.info(f"Cloning {repo_url} at {version}...")
            try:
                subprocess.run(
                    ["git", "clone", "--branch", version, "--depth", "1", repo_url, str(repo_path)],
                    check=True, capture_output=True
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to clone: {e.stderr}")
                return

            INDICES_DIR.mkdir(parents=True, exist_ok=True)
            index_filename = f"{repo_id.replace('/', '-')}-{version}.yaml"
            index_path = INDICES_DIR / index_filename
            
            logger.info(f"Generating index for {repo_id} {version}...")
            # Customize namespace if needed. Defaulting to 'google.adk' for adk-python
            namespace = "google.adk" if "adk-python" in repo_id else ""
            
            ranker = TargetRanker(repo_path=str(repo_path), namespace=namespace)
            await ranker.generate(output_yaml_path=str(index_path))
            
            # Validation
            if golden_symbols:
                logger.info(f"Validating golden symbols: {golden_symbols}")
                with open(index_path, "r") as f:
                    index_data = yaml.safe_load(f)
                
                found_symbols = {item["id"] for item in index_data}
                missing = [s for s in golden_symbols if s not in found_symbols]
                
                if missing:
                    logger.error(f"Validation failed! Missing golden symbols: {missing}")
                    if index_path.exists():
                        index_path.unlink()
                    return
                logger.info("Validation passed.")

            # Update Registry
            if "versions" not in info:
                info["versions"] = {}
            
            # We use a relative path for the bundled index
            # Note: server.py's _BUNDLED_DATA points to the 'data' directory
            info["versions"][version] = {
                "index_url": f"indices/{index_filename}"
            }
            info["default_version"] = version
            
            save_registry(self.registry)
            logger.info(f"Successfully added {repo_id}@{version} to registry.")

    def add_repo(self, repo_id: str, repo_url: str, description: str):
        """Adds a new repository to the registry."""
        if "repositories" not in self.registry:
            self.registry["repositories"] = {}
        
        if repo_id in self.registry["repositories"]:
            logger.warning(f"Repository {repo_id} already exists. Updating...")
        
        self.registry["repositories"][repo_id] = {
            "repo_url": repo_url,
            "description": description,
            "versions": {}
        }
        save_registry(self.registry)
        logger.info(f"Added repository {repo_id} to registry.")

async def main():
    parser = argparse.ArgumentParser(description="Manage Codebase Knowledge Registry")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check-updates
    check_parser = subparsers.add_parser("check-updates", help="Check for new tags in git")
    check_parser.add_argument("--repo-id", help="Filter by repository ID")

    # add-version
    add_ver_parser = subparsers.add_parser("add-version", help="Index and add a new version")
    add_ver_parser.add_argument("repo_id", help="Repository ID (e.g., google/adk-python)")
    add_ver_parser.add_argument("version", help="Git tag or branch")
    add_ver_parser.add_argument("--golden", nargs="+", help="Golden symbols to validate")

    # add-repo
    add_repo_parser = subparsers.add_parser("add-repo", help="Add a new repository definition")
    add_repo_parser.add_repo_parser = add_repo_parser.add_argument("repo_id", help="ID (owner/repo)")
    add_repo_parser.add_repo_parser = add_repo_parser.add_argument("repo_url", help="Git URL")
    add_repo_parser.add_repo_parser = add_repo_parser.add_argument("description", help="Description")

    args = parser.parse_args()
    manager = RegistryManager()

    if args.command == "check-updates":
        await manager.check_updates(args.repo_id)
    elif args.command == "add-version":
        await manager.add_version(args.repo_id, args.version, args.golden)
    elif args.command == "add-repo":
        manager.add_repo(args.repo_id, args.repo_url, args.description)

if __name__ == "__main__":
    asyncio.run(main())
