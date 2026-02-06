"""
Registry Automation Tool.

Handles lifecycle management for the Codebase Knowledge Registry.
- check-updates: Scans for new git tags.
- add-version: Generates index for a new version and updates registry.yaml.
"""

import sys
import shutil
import subprocess
import asyncio
from pathlib import Path
from typing import List, Dict, Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

console = Console()

REGISTRY_PATH = Path(__file__).parent / "adk_knowledge_ext/src/adk_knowledge_ext/registry.yaml"
INDICES_DIR = Path(__file__).parent / "adk_knowledge_ext/src/adk_knowledge_ext/data/indices"

def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        console.print(f"[red]Registry not found at {REGISTRY_PATH}[/red]")
        sys.exit(1)
    return yaml.safe_load(REGISTRY_PATH.read_text())

def save_registry(data: dict):
    with open(REGISTRY_PATH, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)

def get_remote_tags(repo_url: str) -> List[str]:
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

@click.group()
def cli():
    """Manage the Codebase Knowledge Registry."""
    pass

@cli.command()
def check_updates():
    """Check for new versions of registered repositories."""
    data = load_registry()
    repos = data.get("repositories", {})
    
    table = Table(title="Registry Updates")
    table.add_column("Repository", style="cyan")
    table.add_column("Current Versions", style="green")
    table.add_column("New Available", style="yellow")
    
    for repo_id, meta in repos.items():
        repo_url = meta["repo_url"]
        current_versions = set(meta.get("versions", {}).keys())
        
        with console.status(f"Checking {repo_id}...", spinner="dots"):
            remote_tags = get_remote_tags(repo_url)
        
        # Simple semantic version filtering (starts with v, no beta/rc for now)
        # You might want more complex logic later
        stable_tags = [t for t in remote_tags if t.startswith("v") and "rc" not in t and "beta" not in t]
        
        missing = [t for t in stable_tags if t not in current_versions]
        
        # Limit to top 3 newest missing
        missing_display = ", ".join(missing[:3]) if missing else "[dim]Up to date[/dim]"
        
        table.add_row(
            repo_id,
            ", ".join(sorted(current_versions, reverse=True)[:3]),
            missing_display
        )
        
    console.print(table)

@cli.command()
@click.argument("repo_id")
@click.argument("version")
@click.option("--force", is_flag=True, help="Overwrite existing version.")
@click.option("--golden", multiple=True, help="Golden symbols to validate (can be specified multiple times).")
def add_version(repo_id: str, version: str, force: bool, golden: List[str]):
    """Generate index and add version to registry."""
    data = load_registry()
    repos = data.get("repositories", {})
    
    if repo_id not in repos:
        console.print(f"[red]Repository '{repo_id}' not found in registry.[/red]")
        sys.exit(1)
        
    repo_meta = repos[repo_id]
    
    if version in repo_meta.get("versions", {}) and not force:
        console.print(f"[yellow]Version '{version}' already exists for '{repo_id}'. Use --force to overwrite.[/yellow]")
        sys.exit(0)
        
    repo_url = repo_meta["repo_url"]
    
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
        
    # 2. Index
    console.print("[bold]Generating Knowledge Index...[/bold]")
    
    # Create hierarchical directory: indices / safe_repo_id / version
    safe_repo_id = repo_id.replace("/", "-")
    version_dir = INDICES_DIR / safe_repo_id / version
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Standardized filename within the version folder
    output_path = version_dir / "ranked_targets.yaml"
    
    # Invoke run_ranker.py as a subprocess to ensure environment isolation/path handling
    ranker_script = Path(__file__).parent / "knowledge" / "target_ranker" / "run_ranker.py"
    
    # Customize namespace if needed. Defaulting to 'google.adk' for adk-python
    namespace = "google.adk" if "adk-python" in repo_id else ""

    # Check if we are running from project root
    cmd = [
        sys.executable,
        str(ranker_script),
        "--repo-path", str(tmp_dir),
        "--output-yaml", str(output_path),
        # Suppress MD output or point to tmp
        "--output-md", str(tmp_dir / "ranked_targets.md")
    ]
    
    if namespace:
        # Note: run_ranker.py doesn't currently have a --namespace flag in the version I saw earlier, 
        # but the TargetRanker class constructor takes it.
        # Let's check run_ranker.py arguments.
        pass

    # Need to set PYTHONPATH to include project root
    env = sys.environ.copy()
    project_root_path = str(Path(__file__).parent.parent)
    env["PYTHONPATH"] = project_root_path
    
    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError:
        console.print("[red]Indexing failed.[/red]")
        sys.exit(1)
        
    # 3. Validation
    if golden:
        console.print(f"[bold]Validating golden symbols: {', '.join(golden)}[/bold]")
        with open(output_path, "r") as f:
            index_data = yaml.safe_load(f)
        
        found_symbols = {item.get("id") or item.get("fqn") for item in index_data}
        missing = [s for s in golden if s not in found_symbols]
        
        if missing:
            console.print(f"[red]Validation failed! Missing golden symbols: {missing}[/red]")
            if output_path.exists():
                output_path.unlink()
            sys.exit(1)
        console.print("[green]Validation passed.[/green]")

    console.print(f"[green]Index generated at {output_path}[/green]")
    
    # 4. Update Registry
    if "versions" not in repo_meta:
        repo_meta["versions"] = {}
        
    repo_meta["versions"][version] = {
        "index_url": f"indices/{safe_repo_id}/{version}/ranked_targets.yaml"
    }
    
    save_registry(data)
    console.print(f"[green]Registry updated. Added {repo_id}@{version}.[/green]")
    
    # Cleanup
    shutil.rmtree(tmp_dir)

@cli.command()
@click.argument("repo_id")
@click.argument("repo_url")
@click.argument("description")
def add_repo(repo_id: str, repo_url: str, description: str):
    """Add a new repository to the registry."""
    data = load_registry()
    if "repositories" not in data:
        data["repositories"] = {}
    
    if repo_id in data["repositories"]:
        console.print(f"[yellow]Repository '{repo_id}' already exists. Updating...[/yellow]")
    
    data["repositories"][repo_id] = {
        "repo_url": repo_url,
        "description": description,
        "default_version": "main",
        "versions": {}
    }
    save_registry(data)
    console.print(f"[green]Added repository '{repo_id}' to registry.[/green]")

if __name__ == "__main__":
    cli()
