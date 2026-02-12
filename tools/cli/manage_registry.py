"""
Registry Automation Tool.

Handles lifecycle management for the Codebase Knowledge Registry using Pydantic models for validation.
- check-updates: Scans for new git tags.
- add-version: Generates index for a new version and updates registry.yaml.
"""

import sys
import os
import shutil
import subprocess
import asyncio
from pathlib import Path
from typing import List, Dict, Optional

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from pydantic import BaseModel, Field
import questionary
from packaging.version import parse as parse_version

# --- Path Setup ---
from core.config import PROJECT_ROOT

from tools.knowledge.target_ranker.ranker import TargetRanker
from tools.knowledge.build_vector_index import build_index
from tools.knowledge.run_cooccurrence_indexing import generate_cooccurrence

console = Console()

REGISTRY_PATH = PROJECT_ROOT / "tools/adk_knowledge_ext/src/adk_knowledge_ext/registry.yaml"
INDICES_DIR = PROJECT_ROOT / "tools/adk_knowledge_ext/src/adk_knowledge_ext/data/indices"

RANKED_TARGETS_YAML = "ranked_targets.yaml"
RANKED_TARGETS_MD = "ranked_targets.md"

# --- Data Models ---

class VersionInfo(BaseModel):
    """Metadata for a specific version of a repository."""
    index_url: str = Field(..., description="Relative path to the ranked_targets.yaml index.")

class Repository(BaseModel):
    """Metadata for a repository in the registry."""
    repo_url: str = Field(..., description="HTTPS URL of the git repository.")
    description: str = Field("", description="Human-readable description of the repository.")

    sample_repos: List[str] = Field(default_factory=list, description="External repositories to scan for co-occurrence statistics")
    versions: Dict[str, VersionInfo] = Field(default_factory=dict, description="Map of version tags to their metadata.")

class Registry(BaseModel):
    """Root model for the registry.yaml file."""
    repositories: Dict[str, Repository] = Field(default_factory=dict, description="Map of repository IDs to their metadata.")

# --- Storage ---

def load_registry() -> Registry:
    """
    Load and validate the registry from disk.

    Returns:
        Registry: The validated registry object.
    
    Raises:
        SystemExit: If the registry file does not exist.
    """
    if not REGISTRY_PATH.exists():
        console.print(f"[red]Registry not found at {REGISTRY_PATH}[/red]")
        sys.exit(1)
    
    try:
        raw_data = yaml.safe_load(REGISTRY_PATH.read_text()) or {}
        return Registry(**raw_data)
    except Exception as e:
        console.print(f"[red]Failed to parse registry: {e}[/red]")
        sys.exit(1)

def save_registry(registry: Registry) -> None:
    """
    Save the registry to disk.

    Args:
        registry: The registry object to save.
    """
    data = registry.model_dump(mode='json')
    with open(REGISTRY_PATH, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)

# --- Git Utils ---

def get_remote_tags(repo_url: str) -> List[str]:
    """
    Fetch remote tags for a git repository.

    Args:
        repo_url: The HTTPS URL of the repository.

    Returns:
        List[str]: A list of tag names (e.g., 'v1.0.0').
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "--refs", "--sort=-v:refname", repo_url],
            capture_output=True,
            text=True,
            check=True
        )
        tags = []
        for line in result.stdout.splitlines():
            # hash refs/tags/v1.2.3
            parts = line.split("\t")
            if len(parts) == 2:
                ref = parts[1]
                tag = ref.replace("refs/tags/", "")
                tags.append(tag)
        return tags
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to fetch tags for {repo_url}: {e}[/red]")
        return []

def find_available_updates(repos: Dict[str, Repository]) -> Dict[str, List[str]]:
    """
    Check for available updates (new tags) for given repositories.

    Args:
        repos: Dictionary mapping repo_id to Repository objects.

    Returns:
        Dict[str, List[str]]: Map of repo_id to list of new version tags.
    """
    updates = {}
    for repo_id, repo in repos.items():
        current_versions = set(repo.versions.keys())
        
        with console.status(f"Checking {repo_id}...", spinner="dots"):
            remote_tags = get_remote_tags(repo.repo_url)
        
        # Filter for stable releases (v* without beta/rc)
        stable_tags = [t for t in remote_tags if t.startswith("v") and "rc" not in t and "beta" not in t]
        
        if stable_tags:
            updates[repo_id] = stable_tags
            
    return updates

# --- CLI ---

@click.group()
def cli():
    """Manage the Codebase Knowledge Registry."""
    pass

@cli.command()
def check_updates() -> None:
    """Check for new versions of registered repositories."""
    registry = load_registry()
    repos = registry.repositories
    
    updates = find_available_updates(repos)
    
    table = Table(title="Registry Updates")
    table.add_column("Repository", style="cyan")
    table.add_column("Current Versions", style="green")
    table.add_column("New Available", style="yellow")
    
    for repo_id, repo in repos.items():
        current_versions = sorted(repo.versions.keys(), reverse=True)
        available = updates.get(repo_id, [])
        missing = [v for v in available if v not in repo.versions]
        
        # Limit to top 3 newest missing
        missing_display = ", ".join(missing[:3]) if missing else "[dim]Up to date[/dim]"
        
        table.add_row(
            repo_id,
            ", ".join(current_versions[:3]),
            missing_display
        )
        
    console.print(table)

@cli.command()
def update() -> None:
    """Interactively update repositories."""
    registry = load_registry()
    repos = registry.repositories
    
    updates = find_available_updates(repos)
    
    if not updates:
        console.print("[green]No remote versions found![/green]")
        return

    # Flatten updates for selection
    selection_options = []
    # (repo_id, version, is_installed)
    for repo_id, all_versions in updates.items():
        installed = repos[repo_id].versions
        # Identify new versions
        for version in all_versions:
             is_installed = version in installed
             selection_options.append((repo_id, version, is_installed))
    
    table = Table(title="Available Versions")
    table.add_column("Index", justify="right", style="cyan")
    table.add_column("Repository", style="magenta")
    table.add_column("Version", style="green")
    table.add_column("Status", style="blue")
    
    for i, (repo_id, version, is_installed) in enumerate(selection_options):
        status = "[dim]Installed[/dim]" if is_installed else "[bold yellow]New[/bold yellow]"
        table.add_row(str(i + 1), repo_id, version, status)
        
    console.print(table)
    
    choices = [
        questionary.Choice(
            title=f"{repo_id} {version} {'(Installed)' if is_installed else '(New)'}", 
            value=i
        )
        for i, (repo_id, version, is_installed) in enumerate(selection_options)
    ]
    
    result = questionary.checkbox("Select versions to install/update:", choices=choices).ask()
    if result is None:
        return # Cancelled
        
    selected_indices = result
            
    to_process = []
    for idx in selected_indices:
        if 0 <= idx < len(selection_options):
            to_process.append(selection_options[idx])
            
    if not to_process:
        console.print("No updates selected.")
        return
        
    for repo_id, version, is_installed in to_process:
        action = "Reinstalling" if is_installed else "Installing"
        console.print(f"\n[bold]{action} {repo_id} {version}...[/bold]")
        try:
            # Force IS required if it's already installed
            asyncio.run(process_version_update(repo_id, version, force=is_installed, registry=registry))
        except Exception as e:
            import traceback
            traceback.print_exc()
            console.print(f"[red]Failed to update {repo_id}@{version}: {e}[/red]")
            if not Confirm.ask("Continue with remaining updates?", default=True):
                break

async def process_version_update(
    repo_id: str, 
    version: str, 
    force: bool, 
    registry: Optional[Registry] = None
) -> None:
    """
    Generate index and add version to registry.

    Args:
        repo_id: The repository identifier (e.g., 'google/adk-python').
        version: The git tag to index (e.g., 'v1.0.0').
        force: Whether to overwrite an existing version.
        registry: Optional registry object to update. If None, loads from disk.
    """
    # Reload registry if not provided to ensure we have latest state
    if registry is None:
        registry = load_registry()
    
    repos = registry.repositories
    
    if repo_id not in repos:
        console.print(f"[red]Repository '{repo_id}' not found in registry.[/red]")
        sys.exit(1)
        
    repo = repos[repo_id]
    
    if version in repo.versions and not force:
        console.print(f"[yellow]Version '{version}' already exists for '{repo_id}'. Use --force to overwrite.[/yellow]")
        return
        
    repo_url = repo.repo_url
    
    # 1. Clone
    tmp_dir = Path.home() / ".mcp_cache" / "tmp_build" / repo_id.replace("/", "_") / version
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[bold]Cloning {repo_url} ({version})...[/bold]")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", version, repo_url, str(tmp_dir)],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError:
        console.print(f"[red]Failed to clone {repo_url} at tag {version}.[/red]")
        sys.exit(1)
        
    # 1.5 Clone Sample Repos
    scan_targets = [tmp_dir]
    sample_repos = repo.sample_repos
    if sample_repos:
        import re
        samples_dir = tmp_dir / "samples"
        samples_dir.mkdir(parents=True, exist_ok=True)
        for i, sample_url in enumerate(sample_repos):
            sample_dir = samples_dir / f"sample_{i}"
            console.print(f"[bold]Cloning sample repo {sample_url}...[/bold]")
            try:
                # Handle URLs like: https://github.com/google/adk-samples/tree/main/python/agents
                match = re.match(r"(https://github\.com/[^/]+/[^/]+?)(?:\.git)?/tree/([^/]+)/(.*)", sample_url)
                
                if match:
                    base_url = match.group(1)
                    if not base_url.endswith(".git"):
                        base_url += ".git"
                    branch = match.group(2)
                    subpath = match.group(3)
                    
                    subprocess.run(
                        ["git", "clone", "--depth", "1", "--branch", branch, base_url, str(sample_dir)],
                        check=True,
                        capture_output=True
                    )
                    
                    target_path = sample_dir / subpath
                    if target_path.exists():
                        scan_targets.append(target_path)
                    else:
                        console.print(f"[yellow]Warning: Subpath '{subpath}' not found in {sample_url}[/yellow]")
                else:
                    subprocess.run(
                        ["git", "clone", "--depth", "1", sample_url, str(sample_dir)],
                        check=True,
                        capture_output=True
                    )
                    scan_targets.append(sample_dir)
            except subprocess.CalledProcessError as e:
                console.print(f"[yellow]Warning: Failed to clone sample repo {sample_url}: {e}[/yellow]")

    # 2. Generate Co-occurrence Metrics
    console.print("[bold]Generating Co-occurrence Metrics...[/bold]")
    safe_repo_id = repo_id.replace("/", "-")
    version_dir = INDICES_DIR / safe_repo_id / version
    version_dir.mkdir(parents=True, exist_ok=True)
    
    cooccurrence_path = version_dir / "adk_cooccurrence.yaml"
    
    try:
        console.print("[dim]Dynamic discovery enabled (ignoring stdlib)...[/dim]")
        
        console.print(f"[dim]Passing {len(scan_targets)} localized targets to metrics indexer...[/dim]")
        generate_cooccurrence(scan_targets, str(cooccurrence_path))
        console.print(f"[green]✓ Co-occurrence metrics generated at {cooccurrence_path.name}[/green]")
    except Exception as e:
        import traceback
        traceback.print_exc()
        console.print(f"[red]Fatal Error: Co-occurrence generation completely failed: {e}[/red]")
        raise e

    # 3. Index
    console.print("[bold]Generating Knowledge Index...[/bold]")
    
    # Standardized filename within the version folder
    output_path = version_dir / RANKED_TARGETS_YAML
    output_md_path = tmp_dir / RANKED_TARGETS_MD
    
    try:
        # Use simple default stats file location assumed relative to project root or tool
        stats_file = PROJECT_ROOT / "ai/instructions/knowledge/adk_stats_samples.yaml"
        
        ranker = TargetRanker(
            repo_path=str(tmp_dir), 
            stats_file=str(stats_file),
            cooccurrence_file=str(cooccurrence_path) if cooccurrence_path.exists() else None
        )
        await ranker.generate(output_yaml_path=str(output_path), output_md_path=str(output_md_path))
        
    except Exception as e:
        console.print(f"[red]Indexing failed: {e}[/red]")
        sys.exit(1)
        
    console.print(f"[green]Index generated at {output_path}[/green]")

    # 3. Generate Semantic Embeddings
    console.print("[bold]Generating Semantic Embeddings...[/bold]")
    
    try:
        await build_index(output_path)
        console.print("[green]Embeddings generated successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Embedding generation failed: {e}[/red]")
        sys.exit(1)
    
    # 4. Update Registry
    relative_index_path = f"indices/{safe_repo_id}/{version}/{RANKED_TARGETS_YAML}"
    repo.versions[version] = VersionInfo(index_url=relative_index_path)
    
    save_registry(registry)
    console.print(f"[green]Registry updated. Added {repo_id}@{version}.[/green]")
    
    # Cleanup
    shutil.rmtree(tmp_dir)

@cli.command()
@click.argument("repo_id")
@click.argument("version")
@click.option("--force", is_flag=True, help="Overwrite existing version.")
def add_version(repo_id: str, version: str, force: bool):
    """Generate index and add version to registry."""
    try:
        asyncio.run(process_version_update(repo_id, version, force))
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

@cli.command()
@click.argument("repo_id")
@click.argument("repo_url")
@click.argument("description")
def add_repo(repo_id: str, repo_url: str, description: str):
    """Add a new repository to the registry."""
    registry = load_registry()
    repos = registry.repositories
    
    if repo_id in repos:
        console.print(f"[yellow]Repository '{repo_id}' already exists. Updating...[/yellow]")
    
    # Preserve existing versions if updating
    existing_versions = repos[repo_id].versions if repo_id in repos else {}
    
    repos[repo_id] = Repository(
        repo_url=repo_url,
        description=description,
        versions=existing_versions
    )
    
    save_registry(registry)
    console.print(f"[green]Added/Updated repository '{repo_id}' in registry.[/green]")

if __name__ == "__main__":
    cli()
