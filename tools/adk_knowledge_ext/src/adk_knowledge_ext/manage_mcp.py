# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MCP server management commands."""

import json
import subprocess
import os
import sys
import shutil
import yaml
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from pydantic import BaseModel, TypeAdapter
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import reader for pre-cloning
try:
    from .reader import SourceReader
except ImportError:
    # If running as script
    from adk_knowledge_ext.reader import SourceReader

console = Console()


class KBDefinition(BaseModel):
    """Full definition of a Knowledge Base.

    Attributes:
        id (str): Unique ID (owner/repo@version).
        repo_url (str): Git clone URL.
        version (str): Specific tag/branch.
        index_url (Optional[str]): URL for pre-computed index.
        description (Optional[str]): Human-readable summary.
    """

    id: str
    repo_url: str
    version: str
    index_url: Optional[str] = None
    description: Optional[str] = None


class McpServerConfig(BaseModel):
    """The configuration for an MCP server instance.

    Attributes:
        command (str): The binary to run (e.g. 'uvx').
        args (List[str]): List of command line arguments.
        env (Dict[str, str]): Environment variables for the server process.
    """

    command: str
    args: List[str]
    env: Dict[str, str]


class VersionEntry(BaseModel):
    """Metadata for a specific version of a repository.
    
    Attributes:
        index_url: URL to the pre-computed index for this version.
        description: Human-readable description of the version.
    """
    index_url: Optional[str] = None
    description: Optional[str] = None

class RepositoryEntry(BaseModel):
    """Definition of a repository available in the registry.
    
    Attributes:
        description: General description of the repository.
        repo_url: Git clone URL.
        default_version: Version to use if none specified.
        versions: Map of version names to their metadata.
    """
    description: str
    repo_url: str
    default_version: str
    versions: Dict[str, VersionEntry]

    @property
    def label(self) -> str:
        """Returns a formatted label for display."""
        return f"{self.repo_url} (Default: {self.default_version})"

def ask_confirm(question: str, default: bool = True) -> bool:
    """Case-insensitive confirmation prompt using Rich.
    
    Args:
        question (str): The text to display to the user.
        default (bool): The default answer if user presses Enter.
        
    Returns:
        bool: True if user confirmed, False otherwise.
    """
    # Explicitly disable case sensitivity to handle 'Y'/'y' equally
    return Confirm.ask(question, default=default, case_sensitive=False)


MCP_SERVER_NAME = "codebase-knowledge"

def _get_platform_config_path(app_name: str, config_file: str) -> Path:
    """Helper to determine config path based on OS and application.
    
    Args:
        app_name (str): Name of the application (e.g., 'Cursor', 'Windsurf').
        config_file (str): Filename to look for.
        
    Returns:
        Path: Absolute path to the configuration file.
    """
    if sys.platform == "darwin":
        # macOS paths
        if app_name == "Cursor":
            # Cursor commonly uses ~/.cursor for MCP, but app data is in Library
            return Path.home() / ".cursor" / config_file
        elif app_name == "Windsurf":
             return Path.home() / ".codeium" / "windsurf" / config_file
    
    # Default/Linux paths
    if app_name == "Cursor":
        return Path.home() / ".cursor" / config_file
    elif app_name == "Windsurf":
        return Path.home() / ".codeium" / "windsurf" / config_file
        
    folder_name = f".{app_name.lower().replace(' ', '-')}"
    return Path.home() / folder_name / config_file


class IdeConfig(BaseModel):
    """Configuration requirements for a specific IDE or coding agent.
    
    Attributes:
        detect_path: Directory path used to detect if the IDE is installed.
        config_method: Method used to configure ('json' or 'cli').
        start_instruction: Instruction shown to user to start the IDE.
        config_path: Path to the JSON configuration file (for json method).
        config_key: Key within the JSON file where MCP servers are stored.
        cli_command: Binary name in PATH (for cli method).
        cli_scope_flag: Flag for scoping (e.g., --scope).
        cli_scope_value: Value for the scope flag (e.g., user).
        cli_separator: Position of '--' separator in the command.
    """
    detect_path: Path
    config_method: str # Literal["json", "cli"]
    start_instruction: str = ""
    # JSON specific
    config_path: Optional[Path] = None
    config_key: Optional[str] = None
    # CLI specific
    cli_command: Optional[str] = None
    cli_scope_flag: Optional[str] = None
    cli_scope_value: Optional[str] = None
    cli_separator: str = "before_command"

# IDE configuration - how to detect, configure, and start each IDE
IDE_CONFIGS: Dict[str, IdeConfig] = {
    "Claude Code": IdeConfig(
        detect_path=Path.home() / ".claude",
        config_method="cli",
        cli_command="claude",
        cli_scope_flag="--scope",
        cli_scope_value="user",
        cli_separator="before_command",
        start_instruction="Run [cyan]claude[/cyan] in your terminal",
    ),
    "Gemini CLI": IdeConfig(
        detect_path=Path.home() / ".gemini",
        config_method="json",
        config_path=Path.home() / ".gemini" / "settings.json",
        config_key="mcpServers",
        start_instruction="Run [cyan]gemini[/cyan] in your terminal",
    ),
    "Cursor": IdeConfig(
        detect_path=Path.home() / ".cursor",
        config_method="json",
        config_path=Path.home() / ".cursor" / "mcp.json",
        config_key="mcpServers",
        start_instruction="Open [cyan]Cursor[/cyan] app",
    ),
    "Windsurf": IdeConfig(
        detect_path=Path.home() / ".codeium" / "windsurf",
        config_method="json",
        config_path=Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
        config_key="mcpServers",
        start_instruction="Open [cyan]Windsurf[/cyan] app",
    ),
    "Antigravity": IdeConfig(
        detect_path=Path.home() / ".gemini" / "antigravity",
        config_method="json",
        config_path=Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        config_key="mcpServers",
        start_instruction="Open [cyan]Antigravity[/cyan] IDE",
    ),
    "Codex": IdeConfig(
        detect_path=Path.home() / ".codex",
        config_method="cli",
        cli_command="codex",
        cli_separator="before_command",
        start_instruction="Run [cyan]codex[/cyan] in your terminal",
    ),
    "Roo Code": IdeConfig(
        detect_path=Path.home() / ".roo-code",
        config_method="json",
        config_path=Path.home() / ".roo-code" / "mcp.json",
        config_key="mcpServers",
        start_instruction="Open [cyan]Roo Code[/cyan] in VS Code",
    ),
}

def _get_existing_kbs_from_configs() -> List[KBDefinition]:
    """Scans detected IDE configurations for existing Knowledge Base definitions.

    Iterates through all supported IDEs, checks for their configuration files,
    and extracts any existing MCP_KNOWLEDGE_BASES environment variables.

    Returns:
        List[KBDefinition]: A list of KB definitions if found, otherwise an empty list.
    """
    # We prioritize JSON configs as they are easier to parse
    kb_list_adapter = TypeAdapter(List[Union[str, KBDefinition]])

    for ide_name, ide_info in IDE_CONFIGS.items():
        if ide_info.config_method == "json":
            config_path = ide_info.config_path
            config_key = ide_info.config_key

            if config_path and config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Navigate to MCP server config
                    server_conf_raw = data.get(config_key, {}).get(MCP_SERVER_NAME)
                    if server_conf_raw:
                        server_conf = McpServerConfig.model_validate(server_conf_raw)
                        kb_raw = server_conf.env.get("MCP_KNOWLEDGE_BASES")
                        if kb_raw:
                            try:
                                # Try parsing as JSON or CSV
                                if kb_raw.startswith("["):
                                    parsed = kb_list_adapter.validate_json(kb_raw)
                                else:
                                    parsed = [x.strip() for x in kb_raw.split(",") if x.strip()]

                                results: List[KBDefinition] = []
                                for item in parsed:
                                    if isinstance(item, KBDefinition):
                                        results.append(item)
                                    else:
                                        # String ID - create a skeleton
                                        results.append(
                                            KBDefinition(
                                                id=item,
                                                repo_url="Unknown",
                                                version="Unknown",
                                            )
                                        )

                                if results:
                                    return results
                            except Exception:
                                pass
                except Exception:
                    pass
    return []

@click.group()
def cli():
    """Manage the Codebase Knowledge MCP server configuration."""
    pass

@cli.command()
@click.option("--kb-ids", help="Comma-separated list of Knowledge Base IDs to configure (e.g. google/adk-python@v1.20.0)")
@click.option("--repo-url", help="Custom Repository URL (optional)")
@click.option("--version", help="Custom Repository Version (optional)")
@click.option("--index-url", help="Custom Index URL (optional)")
@click.option("--knowledge-index-url", help="Alias for --index-url")
@click.option("--api-key", help="Gemini API Key (optional, for semantic search)")
@click.option("--local", "local_path", required=False, is_flag=False, flag_value=".", help="Use local source directory for the MCP server. Optionally provide path to the package root.")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option("--quiet", "-q", is_flag=True, help="Quiet mode (implies --force)")
def setup(kb_ids: Optional[str], repo_url: Optional[str], version: Optional[str], index_url: Optional[str], knowledge_index_url: Optional[str], api_key: Optional[str], local_path: Optional[str], force: bool, quiet: bool):
    """Auto-configure this MCP server in your coding agents.
    
    This command:
    1. Resolves which Knowledge Bases to use (via CLI args or interactively).
    2. Detects installed IDEs/Coding Agents.
    3. Prompts for merge if existing KBs are found.
    4. Handles cloning (with auth retry if needed).
    5. Writes the configuration to all selected IDEs.

    Args:
        kb_ids (Optional[str]): Comma-separated list of KB IDs.
        repo_url (Optional[str]): Custom Git repository URL.
        version (Optional[str]): Specific version/tag/branch.
        index_url (Optional[str]): Custom index URL.
        knowledge_index_url (Optional[str]): Alias for index_url.
        api_key (Optional[str]): Gemini API Key.
        local_path (Optional[str]): Path to local source code.
        force (bool): Skip confirmation prompts.
        quiet (bool): Suppress output.
    """
    
    local = local_path is not None
    if quiet:
        force = True

    selected_kbs: List[KBDefinition] = []
    github_token = None

    # Handle Custom Repo
    if repo_url:
        ver = version or "main"
        idx = index_url or knowledge_index_url
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        # Generate a temporary ID for custom repos
        custom_id = f"custom/{repo_name}@{ver}"

        selected_kbs.append(
            KBDefinition(
                id=custom_id,
                repo_url=repo_url,
                version=ver,
                index_url=idx,
                description=f"Custom Repository: {repo_url}",
            )
        )

    # Load Registry
    registry_path = Path(__file__).parent / "registry.yaml"
    registry_repos: Dict[str, RepositoryEntry] = {}
    
    if registry_path.exists():
        try:
            data = yaml.safe_load(registry_path.read_text())
            # Support both legacy flat and new hierarchical format
            if "repositories" in data:
                # New Hierarchical Format
                for repo_id, meta in data["repositories"].items():
                    versions = {}
                    for v_id, v_meta in meta.get("versions", {}).items():
                        versions[v_id] = VersionEntry(**v_meta)
                    
                    registry_repos[repo_id] = RepositoryEntry(
                        description=meta["description"],
                        repo_url=meta["repo_url"],
                        default_version=meta["default_version"],
                        versions=versions
                    )
            else:
                # Legacy Flat Format (fallback)
                pass 
        except Exception:
            pass

    # 1. Resolve Selection
    if kb_ids:
        console.print(f"[dim]Pre-selecting Knowledge Bases from list: {kb_ids} (skipping interactive selection)[/dim]")
        # Resolve IDs: owner/repo@version OR owner/repo (default)
        requested_ids = [x.strip() for x in kb_ids.split(",") if x.strip()]
        for rid in requested_ids:
            if "@" in rid:
                # Explicit version
                repo_id, version_arg = rid.split("@", 1)
            else:
                # Default version
                repo_id = rid
                version_arg = None

            if repo_id in registry_repos:
                repo_entry = registry_repos[repo_id]
                target_version = version_arg or repo_entry.default_version
                
                if target_version in repo_entry.versions:
                    v_entry = repo_entry.versions[target_version]
                    selected_kbs.append(
                        KBDefinition(
                            id=f"{repo_id}@{target_version}",
                            repo_url=repo_entry.repo_url,
                            version=target_version,
                            index_url=v_entry.index_url,
                            description=v_entry.description or repo_entry.description,
                        )
                    )
                else:
                    console.print(
                        f"[yellow]Warning: Version '{target_version}' not found for '{repo_id}'[/yellow]"
                    )
            else:
                # Check for legacy flat ID match if needed, or just warn
                console.print(f"[yellow]Warning: Repository '{repo_id}' not found in registry.[/yellow]")

    elif not repo_url:
        # Interactive Mode (only if no custom repo provided)
        if quiet:
            pass
        elif registry_repos:
            console.print("\n[bold]Step 1: Select Repositories[/bold]")
            repo_keys = list(registry_repos.keys())
            for i, r_key in enumerate(repo_keys):
                entry = registry_repos[r_key]
                console.print(f" [{i+1}] {r_key}: {entry.description}")
            
            selection_input = Prompt.ask("\nSelect repositories (comma-separated indices or names)")
            parts = [x.strip() for x in selection_input.split(",")]
            
            selected_repo_entries = []
            for p in parts:
                target_repo = None
                r_id = None
                if p.isdigit():
                    idx = int(p)
                    if 1 <= idx <= len(repo_keys):
                        r_id = repo_keys[idx-1]
                        target_repo = registry_repos[r_id]
                elif p in registry_repos:
                    r_id = p
                    target_repo = registry_repos[p]
                
                if target_repo and target_repo not in [x[1] for x in selected_repo_entries]:
                    selected_repo_entries.append((r_id, target_repo))

            # Step 2: Select Versions for each repo
            if selected_repo_entries:
                console.print("\n[bold]Step 2: Select Versions[/bold]")
                for r_id, repo in selected_repo_entries:
                    versions = list(repo.versions.keys())
                    if len(versions) == 1:
                        target_version = versions[0]
                        console.print(f"   Using only available version for '{r_id}': [cyan]{target_version}[/cyan]")
                    else:
                        console.print(f"\n   Configuring [bold]{r_id}[/bold]:")
                        for j, v_id in enumerate(versions):
                            v_meta = repo.versions[v_id]
                            default_mark = " [dim](Default)[/dim]" if v_id == repo.default_version else ""
                            desc = f" - {v_meta.description}" if v_meta.description else ""
                            console.print(f"    [{j+1}] {v_id}{default_mark}{desc}")
                        
                        # Find default index
                        def_idx = 1
                        try:
                            def_idx = versions.index(repo.default_version) + 1
                        except ValueError:
                            pass

                        v_choice = Prompt.ask(
                            f"   Select version for '{r_id}'", 
                            choices=[str(x+1) for x in range(len(versions))],
                            default=str(def_idx),
                            show_choices=False
                        )
                        target_version = versions[int(v_choice) - 1]

                    v_entry = repo.versions[target_version]
                    selected_kbs.append(
                        KBDefinition(
                            id=f"{r_id}@{target_version}",
                            repo_url=repo.repo_url,
                            version=target_version,
                            index_url=v_entry.index_url,
                            description=v_entry.description or repo.description,
                        )
                    )

    # Merge Check
    if not force:
        existing_kbs = _get_existing_kbs_from_configs()

        # Case 1: User selected nothing new
        if not selected_kbs:
            if existing_kbs:
                console.print(f"\n[yellow]No new repositories selected.[/yellow]")
                console.print(f"Existing configuration found:")
                for kb in existing_kbs:
                    console.print(f" - {kb.id}")

                if not ask_confirm(
                    "Do you want to re-apply the existing configuration?", default=True
                ):
                    console.print("Cancelled.")
                    return

                # Re-apply existing
                selected_kbs = existing_kbs
            else:
                console.print("[red]No repositories selected.[/red]")
                return

        # Case 2: User selected new repos, and we have existing ones
        elif existing_kbs:
            existing_ids = {kb.id for kb in existing_kbs}
            new_ids = {kb.id for kb in selected_kbs}

            # Detect if there's anything to discuss
            if existing_ids != new_ids:
                console.print(
                    f"\n[bold yellow]Existing configuration found:[/bold yellow]"
                )
                for kb in existing_kbs:
                    console.print(f" - {kb.id}")

                if selected_kbs:
                    console.print(f"\n[bold green]New configuration:[/bold green]")
                    for kb in selected_kbs:
                        console.print(f" - {kb.id}")

                if (
                    Prompt.ask(
                        "\nMerge with existing configuration?",
                        choices=["y", "n"],
                        default="y",
                    )
                    == "y"
                ):
                    merged_map = {kb.id: kb for kb in existing_kbs}
                    for kb in selected_kbs:
                        merged_map[kb.id] = kb
                    selected_kbs = list(merged_map.values())
                    console.print(
                        f"[dim]Merged total: {len(selected_kbs)} repositories[/dim]"
                    )

    # Pre-load/Clone Repositories
    if selected_kbs:
        console.print("\n[bold]Pre-loading Knowledge Bases...[/bold]")

        # Check if we already have a GitHub token
        github_token = os.environ.get("GITHUB_TOKEN")

        for kb in selected_kbs:
            try:
                # If we collected a token from a previous failure in this loop, ensure it's in env
                if github_token:
                    os.environ["GITHUB_TOKEN"] = github_token

                reader = SourceReader(kb.repo_url, kb.version)

                if reader.repo_root is None or not reader.repo_root.exists():
                    raise RuntimeError("Clone failed (directory not found)")

                console.print(f"   Using {kb.repo_url} ({kb.version})...")
            except Exception as e:
                console.print(f"   [red]Failed to clone {kb.repo_url}: {e}[/red]")

                # Auth Retry Logic
                if not github_token and not force:
                    if ask_confirm(
                        f"\nClone failed (possibly private repo). Do you want to provide a GitHub Personal Access Token (PAT)?",
                        default=True,
                    ):
                        github_token = Prompt.ask("Enter GitHub Token", password=True)
                        if github_token:
                            os.environ["GITHUB_TOKEN"] = github_token
                            console.print("[dim]Retrying with token...[/dim]")
                            try:
                                reader = SourceReader(kb.repo_url, kb.version)
                                if reader.repo_root and reader.repo_root.exists():
                                    console.print(
                                        f"   [green]Success![/green] Using {kb.repo_url}..."
                                    )
                                else:
                                    console.print("   [red]Retry failed.[/red]")
                            except Exception as retry_e:
                                console.print(f"   [red]Retry failed: {retry_e}[/red]")

    # Optional API Key
    if not force and not api_key and not os.environ.get("GEMINI_API_KEY"):
        if ask_confirm("Do you have a Gemini API Key? (Required for semantic search)", default=False):
            api_key = Prompt.ask("Enter Gemini API Key", password=True)

    console.print()
    console.print(
        Panel(
            "[bold]🚀 Codebase Knowledge MCP Setup[/bold]\n\n"
            + "\n".join([f"- {kb.repo_url} ({kb.version})" for kb in selected_kbs]),
            border_style="blue",
        )
    )

    # Detect IDEs
    console.print("[bold]🔍 Detecting installed coding agents...[/bold]")
    
    detected_ides = {}
    for ide_name, ide_info in IDE_CONFIGS.items():
        is_installed = False
        
        # Check based on method
        if ide_info.config_method == "cli":
            # For CLI, verify binary is in PATH
            if shutil.which(ide_info.cli_command):
                is_installed = True
            elif ide_info.detect_path.exists():
                 # Fallback: Folder exists but not in PATH
                 # We mark as False to avoid 'No such file' error, but we'll show a warning
                 is_installed = False
        else:
            # For JSON, just check dir existence
            if ide_info.detect_path.exists():
                is_installed = True
                
        if is_installed:
            detected_ides[ide_name] = ide_info

    configured_status = {}
    def check_configured(ide_name: str) -> tuple[str, bool]:
        """Helper to check if MCP is already configured in a specific IDE."""
        return ide_name, _is_mcp_configured(ide_name, detected_ides[ide_name])

    if detected_ides:
        with ThreadPoolExecutor(max_workers=len(detected_ides)) as executor:
            results = executor.map(check_configured, detected_ides.keys())
            configured_status = dict(results)

    # Display results
    for ide_name, ide_info in IDE_CONFIGS.items():
        detect_path = ide_info.detect_path
        if ide_name in detected_ides:
            status = "[green](configured)[/green]" if configured_status.get(ide_name) else ""
            console.print(f"   ✓ {ide_name:<15} [dim]{detect_path}[/dim] {status}")
        else:
            # Check if it was a CLI tool that failed verification
            if ide_info.config_method == "cli" and ide_info.detect_path.exists():
                console.print(f"   [yellow]! {ide_name:<15} (config found at {detect_path}, but '{ide_info.cli_command}' not in PATH)[/yellow]")
            else:
                console.print(f"   [dim]✗ {ide_name:<15} (not installed)[/dim]")

    if not detected_ides:
        console.print("[yellow]No supported coding agents detected.[/yellow]")
        return

    # Select IDEs
    selected_ides = {}
    if force:
        selected_ides = detected_ides
    else:
        console.print("\n[bold]Which coding agents would you like to configure?[/bold]")
        for ide_name in detected_ides:
            default_val = not configured_status.get(ide_name, False)
            if ask_confirm(f"   Configure {ide_name}?", default=default_val):
                selected_ides[ide_name] = detected_ides[ide_name]

    if not selected_ides:
        console.print("No IDEs selected.")
        return

    # Plan Changes
    console.print("\n[bold]Configuration Plan[/bold]")
    files_to_modify = []
    commands_to_run = []
    
    for ide_name, ide_info in selected_ides.items():
        if ide_info.config_method == "json":
            p = ide_info.config_path
            files_to_modify.append((ide_name, p))
        elif ide_info.config_method == "cli":
            commands_to_run.append(f"{ide_info.cli_command} mcp add ... (configuring {ide_name})")

    if files_to_modify:
        console.print("\n[yellow]The following configuration files will be updated:[/yellow]")
        for name, p in files_to_modify:
            status = "(modifying)" if p.exists() else "(creating)"
            console.print(f"   - [bold]{name}[/bold]: {p} {status}")
            if p.exists():
                console.print(f"     [dim]A backup will be created at {p}.bak[/dim]")

    if commands_to_run:
        console.print("\n[yellow]The following commands will be executed:[/yellow]")
        for cmd in commands_to_run:
            console.print(f"   - {cmd}")
            
    if not force:
        if not ask_confirm("\nProceed with these changes?", default=True):
            console.print("Cancelled.")
            return

    # Configure
    console.print("\n[bold]Applying configuration...[/bold]")
    # Resolve local path if provided as a flag but empty, or use the provided string
    resolved_local_path = None
    if local:
        # If run as --local (flag only), local_path might be empty string or True depending on click config, 
        # but here we changed it to a non-flag option. If user wants current dir, they can pass '.' or we handle None.
        # Actually, let's make it robust:
        resolved_local_path = local_path if local_path else "."

    mcp_config = _generate_mcp_config(selected_kbs, api_key, github_token, resolved_local_path)

    for ide_name, ide_info in selected_ides.items():
        try:
            _configure_ide(ide_name, ide_info, mcp_config)
            console.print(f"✅ {ide_name} configured")
        except Exception as e:
            console.print(f"[red]❌ {ide_name} failed: {e}[/red]")

    console.print("\n[bold green]🎉 Setup complete![/bold green]")


@cli.command()
@click.option("--quiet", "-q", is_flag=True, help="Quiet mode (skips confirmation prompts and suppresses output)")
def remove(quiet: bool):
    """Remove this MCP server configuration from coding agents.

    Checks all supported IDEs for the codebase-knowledge server and
    prompts the user to remove it from each one.

    Args:
        quiet (bool): Suppress output and skip confirmation prompts.
    """
    if not quiet:
        console.print("\n[bold]🗑️  Codebase Knowledge MCP Remove[/bold]\n")

    configured_ides = {}
    for ide_name, ide_info in IDE_CONFIGS.items():
        # For CLI tools, we need the binary to check config (mcp list)
        is_runnable = True
        if ide_info.config_method == "cli" and not shutil.which(ide_info.cli_command):
            is_runnable = False

        if (
            ide_info.detect_path.exists()
            and is_runnable
            and _is_mcp_configured(ide_name, ide_info)
        ):
            configured_ides[ide_name] = ide_info
            if not quiet:
                console.print(f"   ✓ {ide_name:<15} [green]configured[/green]")

    if not configured_ides:
        if not quiet:
            console.print("[yellow]No coding agents have this MCP configured.[/yellow]")
        return

    selected_ides = {}

    if quiet:
        selected_ides = configured_ides
    else:
        console.print("\n[bold]Remove from:[/bold]")
        for ide_name in configured_ides:
            if ask_confirm(f"   {ide_name}", default=True):
                selected_ides[ide_name] = configured_ides[ide_name]

    if not selected_ides:
        return

    for ide_name, ide_info in selected_ides.items():
        try:
            _remove_mcp_config(ide_name, ide_info)
            if not quiet:
                console.print(f"✅ {ide_name} - removed")
        except Exception as e:
            if not quiet:
                console.print(f"[red]❌ {ide_name} failed: {e}[/red]")


@cli.command()
def debug():
    """Diagnose the MCP server installation and configuration.
    
    Performs the following checks:
    1. Version Information (Git SHA, Python, Platform).
    2. Server Self-Test (Connection, Tools, Knowledge Bases).
    3. File System & Paths (Cache, Instructions, Indices, Logs).
    4. Environment Variables (API Keys, Token).
    5. IDE Integration Status (Command, Args, Env).
    """
    console.print("\n[bold blue]🕵️  Codebase Knowledge MCP Debugger[/bold blue]")
    
    # 1. Version Info
    try:
        from ._version_git import GIT_SHA
        version_str = f"Git SHA: {GIT_SHA}"
    except ImportError:
        version_str = "Git SHA: Unknown (Source/Dev)"
    
    console.print(f"\n[bold]1. Version Information[/bold]")
    console.print(f"   {version_str}")
    console.print(f"   Python: {sys.version.split()[0]}")
    console.print(f"   Platform: {sys.platform}")

    # 2. Server Self-Test
    console.print(f"\n[bold]2. Server Self-Test[/bold]")
    
    env = os.environ.copy()
    if "MCP_KNOWLEDGE_BASES" in env:
        del env["MCP_KNOWLEDGE_BASES"]
    
    console.print("   [dim]Scanning IDE configurations...[/dim]")
    
    ide_configs_found = []
    
    for ide_name, ide_info in IDE_CONFIGS.items():
        if _is_mcp_configured(ide_name, ide_info):
            ide_configs_found.append((ide_name, ide_info))
            
    if not ide_configs_found:
        console.print("   [yellow]No integrations configured. Running generic server test with bundled registry.[/yellow]")
        server_env = env
    else:
        console.print(f"   Found configurations for: {', '.join(n for n, _ in ide_configs_found)}")
        target_conf = None
        for name, info in ide_configs_found:
            if info.config_method == "json":
                try:
                    with open(info.config_path) as f:
                        data = json.load(f)
                        mcp_conf = data[info.config_key][MCP_SERVER_NAME]
                        target_conf = mcp_conf.get("env", {})
                        break
                except Exception:
                    pass
        
        if not target_conf:
            console.print("   [yellow]Could not extract env from configurations (CLI-only?). Using default.[/yellow]")
            server_env = env
        else:
            server_env = env
            server_env.update(target_conf)

    # Use sys.executable to run the module
    server_cmd = [sys.executable, "-m", "adk_knowledge_ext.server"]
    
    async def run_diagnostics():
        """Internal helper to run async diagnostics."""
        nonlocal critical_failure_found
        # Set environment to force unbuffered output if possible, though mcp handles stdio
        server_env["PYTHONUNBUFFERED"] = "1"
        server_env["MCP_LOG_INDENT"] = "   "
        
        server_params = StdioServerParameters(
            command=server_cmd[0],
            args=server_cmd[1:],
            env=server_env
        )
        
        console.print(f"   Starting server with command: {' '.join(server_cmd)}")
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 1. List Tools
                    tools_result = await session.list_tools()
                    tool_names = [t.name for t in tools_result.tools]
                    console.print(f"   ✅ Server Connection: OK")
                    console.print(f"   🛠️  Tools Available: {', '.join(tool_names)}")
                    
                    if "list_modules" not in tool_names:
                        console.print("   [red]CRITICAL: list_modules tool missing![/red]")
                        return

                    # 2. Inspect KBs
                    kbs_raw = server_env.get("MCP_KNOWLEDGE_BASES")
                    kbs_to_test: List[Union[str, KBDefinition]] = []
                    if kbs_raw:
                        try:
                            # Use TypeAdapter for robust parsing
                            adapter = TypeAdapter(List[Union[str, KBDefinition]])
                            if kbs_raw.startswith("["):
                                kbs_to_test = adapter.validate_json(kbs_raw)
                            else:
                                # String list
                                kbs_to_test = [
                                    x.strip() for x in kbs_raw.split(",") if x.strip()
                                ]
                        except Exception:
                            pass

                    if not kbs_to_test:
                        # Add a dummy KB definition for testing default
                        kbs_to_test = [
                            KBDefinition(
                                id="Default/Bundled", repo_url="None", version="None"
                            )
                        ]

                    for kb in kbs_to_test:
                        # Extract ID safely from Union
                        kb_id = kb if isinstance(kb, str) else kb.id
                        label = f"{kb_id}" if kb_id else "Default (Bundled)"

                        console.print(f"   Testing KB: [cyan]{label}[/cyan]")

                        # 1. list_modules
                        first_item_fqn = None
                        try:
                            # Call list_modules
                            args = {"page_size": 5}
                            # Only pass kb_id if it's not the dummy one
                            if kb_id != "Default/Bundled":
                                args["kb_id"] = kb_id

                            console.print(
                                f"      [dim]→ list_modules({json.dumps(args)})[/dim]"
                            )
                            result = await session.call_tool(
                                "list_modules", arguments=args
                            )
                            content = result.content[0].text

                            if result.isError or content.strip().startswith("Error:") or "not found" in content.lower():
                                console.print(f"      ❌ [red]Failed[/red]")
                                console.print(
                                    Panel(
                                        content,
                                        title="Output (Error)",
                                        border_style="red",
                                    )
                                )
                            else:
                                console.print(f"      ✅ [green]OK[/green]")
                                # Increased truncation limit to 1000 chars
                                console.print(
                                    Panel(
                                        content[:1000]
                                        + ("..." if len(content) > 1000 else ""),
                                        title="Output (Truncated)",
                                        border_style="dim",
                                    )
                                )

                                # Extract FQN for next tests
                                import re

                                match = re.search(r"\[.*?\] \w+: (\S+)", content)
                                if match:
                                    first_item_fqn = match.group(1)
                        except Exception as e:
                            console.print(f"      ❌ [red]Error {e}[/red]")

                        # 2. search_knowledge
                        try:
                            q_args = {"queries": ["client"], "limit": 3}
                            if kb_id != "Default/Bundled":
                                q_args["kb_id"] = kb_id

                            console.print(
                                f"      [dim]→ search_knowledge({json.dumps(q_args)})[/dim]"
                            )
                            result = await session.call_tool(
                                "search_knowledge", arguments=q_args
                            )
                            content = result.content[0].text

                            if result.isError or content.strip().startswith("Error:") or "not found" in content.lower():
                                console.print(f"      ❌ [red]Failed[/red]")
                                console.print(
                                    Panel(
                                        content,
                                        title="Output (Error)",
                                        border_style="red",
                                    )
                                )
                            else:
                                console.print(f"      ✅ [green]OK[/green]")
                                console.print(
                                    Panel(
                                        content[:800]
                                        + ("..." if len(content) > 800 else ""),
                                        title="Output (Truncated)",
                                        border_style="dim",
                                    )
                                )
                                
                                # 2.5 Vector Search Capability Check (New)
                                console.print("      [bold cyan]Checking Vector Search capability...[/bold cyan]")
                                # Perform a search with a unique query to trace it in logs
                                test_query = "agent state management"
                                v_args = {"queries": [test_query], "limit": 1}
                                if kb_id != "Default/Bundled":
                                    v_args["kb_id"] = kb_id
                                
                                await session.call_tool("search_knowledge", arguments=v_args)
                                
                                # Inspect logs to verify VectorSearchProvider matched
                                log_path = Path.home() / ".mcp_cache" / "logs" / "codebase-knowledge.log"
                                if log_path.exists():
                                    try:
                                        # Give the server a moment to flush logs
                                        await asyncio.sleep(0.2)
                                        log_lines = log_path.read_text().splitlines()
                                        found_provider = None
                                        # Scan backwards for our test query
                                        for line in reversed(log_lines):
                                            # Check for Composite match
                                            if f"matched for query: '{test_query}'" in line:
                                                if "VectorSearchProvider" in line:
                                                    found_provider = "VectorSearchProvider"
                                                elif "BM25SearchProvider" in line:
                                                    found_provider = "BM25SearchProvider"
                                                elif "KeywordSearchProvider" in line:
                                                    found_provider = "KeywordSearchProvider"
                                                break
                                            # Check for Direct Vector match
                                            if f"VectorSearchProvider searching for query: '{test_query}'" in line:
                                                found_provider = "VectorSearchProvider"
                                                break
                                        
                                        if found_provider == "VectorSearchProvider":
                                            console.print("      ✅ [green]Vector Search: ACTIVE[/green] (confirmed via logs)")
                                        elif found_provider:
                                            console.print(f"      ❌ [red]Vector Search: FAILED[/red] (fell back to {found_provider})")
                                            # Track critical failure
                                            critical_failure_found = True
                                        else:
                                            # If we have API KEY, we expected it to work
                                            if server_env.get("GEMINI_API_KEY"):
                                                console.print("      ❌ [red]Vector Search: FAILED[/red] (trace not found in logs)")
                                                critical_failure_found = True
                                            else:
                                                console.print("      ⚠️  [yellow]Vector Search: SKIPPED[/yellow] (GEMINI_API_KEY not set)")
                                    except Exception as log_e:
                                        console.print(f"      ⚠️  [yellow]Vector Search: Could not verify logs ({log_e})[/yellow]")
                                else:
                                    console.print("      ⚠️  [yellow]Vector Search: Log file missing, cannot verify provider.[/yellow]")
                        except Exception as e:
                            console.print(f"      ❌ [red]Error {e}[/red]")
                            # Track critical failure
                            critical_failure_found = True

                        # 3. inspect_symbol
                        if first_item_fqn:
                            try:
                                i_args = {"fqn": first_item_fqn}
                                if kb_id != "Default/Bundled":
                                    i_args["kb_id"] = kb_id

                                console.print(
                                    f"      [dim]→ inspect_symbol({json.dumps(i_args)})[/dim]"
                                )
                                result = await session.call_tool(
                                    "inspect_symbol", arguments=i_args
                                )
                                content = result.content[0].text

                                    # Check for success
                                import re
                                if result.isError or content.strip().startswith("Error:") or re.match(r"^Symbol '.*' not found", content.strip()):
                                    console.print(f"      ❌ [red]Failed[/red]")
                                    console.print(
                                        Panel(
                                            content,
                                            title="Output (Error)",
                                            border_style="red",
                                        )
                                    )
                                else:
                                    console.print(f"      ✅ [green]OK[/green]")
                                    console.print(
                                        Panel(
                                            content[:800]
                                            + ("..." if len(content) > 800 else ""),
                                            title="Output (Truncated)",
                                            border_style="dim",
                                        )
                                    )
                            except Exception as e:
                                console.print(f"      ❌ [red]Error {e}[/red]")
                        else:
                            console.print(f"      ⚠️  inspect_symbol: Skipped (no FQN found)")

        except Exception as e:
            console.print(f"   [red]Server Start Failed: {e}[/red]")
            console.print("   Check if 'adk_knowledge_ext.server' is importable.")

    critical_failure_found = False
    asyncio.run(run_diagnostics())

    # 3. File System & Paths
    console.print(f"\n[bold]3. File System & Paths[/bold]")
    paths_to_check = [
        ("Base Cache", Path.home() / ".mcp_cache", "Root directory for all persisted MCP data (cloned repos, indices)."),
        ("Instructions", Path.home() / ".mcp_cache" / "instructions", "System instructions injected into LLM contexts."),
        ("Indices", Path.home() / ".mcp_cache" / "indices", "Pre-computed codebase knowledge indices (YAML)."),
        ("Logs", Path.home() / ".mcp_cache" / "logs", "Server execution and error logs."),
        ("Registry", Path(__file__).parent / "registry.yaml", "Bundled list of known repositories and versions.")
    ]
    
    for label, p, desc in paths_to_check:
        if p.exists():
            if p.is_dir():
                try:
                    # Specific counting based on directory type
                    item_list = []
                    if "instructions" in str(p):
                        items = list(p.glob("*.md"))
                        count_str = f"{len(items)} instruction files"
                        item_list = [i.name for i in items]
                    elif "indices" in str(p):
                        items = list(p.glob("*.yaml"))
                        count_str = f"{len(items)} indices"
                        item_list = [i.name for i in items]
                    elif "logs" in str(p):
                        items = list(p.glob("*.log*"))
                        count_str = f"{len(items)} log files"
                        item_list = [i.name for i in items]
                    else:
                        items = [x for x in p.iterdir() if x.is_dir() and not x.name.startswith(".")]
                        count_str = f"{len(items)} cached repos"
                        item_list = [i.name for i in items]
                    
                    console.print(f"   ✓ [bold]{label:<15}[/bold] {p}\n      [dim]└─ {desc}[/dim] [green]({count_str})[/green]")
                    if item_list:
                        # Limit list to 10 items for readability
                        display_items = item_list[:10]
                        if len(item_list) > 10:
                            display_items.append("...")
                        console.print(f"      [dim]   Items: {', '.join(display_items)}[/dim]")
                except Exception as e:
                    console.print(f"   ✓ [bold]{label:<15}[/bold] {p}\n      [dim]└─ {desc}[/dim] [yellow](Unreadable: {e})[/yellow]")
            else:
                size = p.stat().st_size
                console.print(f"   ✓ [bold]{label:<15}[/bold] {p}\n      [dim]└─ {desc}[/dim] [green]({size} bytes)[/green]")
        else:
            console.print(f"   ✗ [bold]{label:<15}[/bold] {p}\n      [dim]└─ {desc}[/dim] [red](Missing)[/red]")

    # 4. Environment
    console.print(f"\n[bold]4. Environment Variables[/bold]")
    vars_to_check = [
        ("GEMINI_API_KEY", "Used for semantic/vector search and LLM-based tools."),
        ("MCP_KNOWLEDGE_BASES", "JSON list of active repositories for this session."),
        ("GITHUB_TOKEN", "Optional: Used to avoid rate limits when downloading indices or cloning.")
    ]
    for v, desc in vars_to_check:
        val = os.environ.get(v)
        if val:
            display = "[green]Set[/green]"
            if v == "MCP_KNOWLEDGE_BASES":
                display += f" ({len(val)} chars)"
            else:
                display += " (Masked)"
            console.print(f"   ✓ [bold]{v:<20}[/bold] {display}\n      [dim]└─ {desc}[/dim]")
        else:
            console.print(f"   - [bold]{v:<20}[/bold] [dim]Not set[/dim]\n      [dim]└─ {desc}[/dim]")

    # 5. Integrations Check
    console.print(f"\n[bold]5. Integration Status[/bold]")
    found_any = False
    
    for ide_name, ide_info in IDE_CONFIGS.items():
        if _is_mcp_configured(ide_name, ide_info):
            found_any = True
            console.print(f"   ✓ {ide_name}")
            
            # CLI Checks
            if ide_info.config_method == "cli":
                cmd = ide_info.cli_command
                try:
                    res = subprocess.run([cmd, "mcp", "list"], capture_output=True, text=True, timeout=5)
                    if MCP_SERVER_NAME in res.stdout or MCP_SERVER_NAME in res.stderr:
                         console.print(f"      - CLI Status: [green]Verified[/green] (found in registry)")
                    else:
                         console.print(f"      - CLI Status: [yellow]Not found in output[/yellow]")
                except Exception:
                     console.print(f"      - CLI Status: [red]Command failed[/red]")
            
            # JSON Checks
            elif ide_info.config_method == "json":
                try:
                    with open(ide_info.config_path, "r") as f:
                        config = json.load(f)
                    
                    server_conf = config.get(ide_info.config_key, {}).get(MCP_SERVER_NAME)
                    if not server_conf:
                        console.print(f"      - Config: [red]Missing entry[/red]")
                        continue
                        
                    cmd = server_conf.get("command")
                    args = server_conf.get("args", [])
                    env_vars = server_conf.get("env", {})
                    
                    # 1. Check Command
                    if shutil.which(cmd):
                        console.print(f"      - Command '{cmd}': [green]Found[/green]")
                    else:
                        console.print(f"      - Command '{cmd}': [red]Not found in PATH[/red]")
                        
                    # 2. Check Paths in Args
                    for i, arg in enumerate(args):
                        if arg == "--from" and i + 1 < len(args):
                            path_arg = args[i+1]
                            if not path_arg.startswith("git+"):
                                p = Path(path_arg).expanduser().resolve()
                                if p.exists():
                                     console.print(f"      - Source Path: [green]Exists[/green]")
                                else:
                                     console.print(f"      - Source Path '{p}': [red]Not found[/red]")

                    # 3. Check Env Vars (KB Config)
                    if "MCP_KNOWLEDGE_BASES" in env_vars:
                        try:
                            kbs = json.loads(env_vars["MCP_KNOWLEDGE_BASES"])
                            console.print(f"      - KBs Configured: {len(kbs)}")
                        except json.JSONDecodeError:
                            console.print(f"      - KBs Configured: [red]Invalid JSON[/red]")
                    
                except Exception as e:
                    console.print(f"      - Config Check: [red]Error reading config: {e}[/red]")

    if not found_any:
        console.print("   [yellow]No active integrations found for this MCP server.[/yellow]")
        console.print("   The following application directories were checked:")
        for ide_name, ide_info in IDE_CONFIGS.items():
             detect_path = ide_info.detect_path
             if detect_path:
                 status = "[red]Not found[/red]" if not detect_path.exists() else "[yellow]App found, but MCP not configured[/yellow]"
                 console.print(f"   - {ide_name:<15}: {detect_path} {status}")

    # At the end of debug command, if critical failure found, exit with error
    if critical_failure_found:
        console.print("\n[bold red]FATAL: One or more critical capability checks failed.[/bold red]")
        sys.exit(1)


def _generate_mcp_config(
    selected_kbs: List[KBDefinition],
    api_key: Optional[str],
    github_token: Optional[str] = None,
    local_path: Optional[str] = None,
) -> McpServerConfig:
    """Generate the MCP server configuration.

    Args:
        selected_kbs (List[KBDefinition]): List of knowledge base definitions.
        api_key (Optional[str]): Gemini API key for semantic search.
        github_token (Optional[str]): GitHub PAT for private repo cloning.
        local_path (Optional[str]): Optional path to local source code.

    Returns:
        McpServerConfig: A validated configuration object for the MCP server.
    """

    # Enrich KBs with registry info if index_url missing
    import yaml

    registry_path = Path(__file__).parent / "registry.yaml"
    registry = {}
    if registry_path.exists():
        try:
            registry = yaml.safe_load(registry_path.read_text())
        except Exception:
            pass

    final_kbs: List[Union[str, KBDefinition]] = []

    for kb in selected_kbs:
        # Check if this KB is in the bundled registry
        match_found = False

        if "repositories" in registry:
            for repo_id, meta in registry["repositories"].items():
                if meta.get("repo_url") == kb.repo_url:
                    # check version
                    if kb.version in meta.get("versions", {}):
                        # Found exact match
                        # Verify if ID matches what we expect
                        expected_id = f"{repo_id}@{kb.version}"
                        if kb.id == expected_id:
                            match_found = True
                        # Also handle default alias
                        elif (
                            kb.version == meta.get("default_version")
                            and kb.id == repo_id
                        ):
                            match_found = True
                        break
        else:
            # Legacy flat format
            if kb.id in registry:
                meta = registry[kb.id]
                if (
                    meta.get("repo_url") == kb.repo_url
                    and meta.get("version") == kb.version
                ):
                    match_found = True

        if match_found:
            # It's a standard bundled KB, just save the ID string
            final_kbs.append(kb.id)
        else:
            # Custom or overridden KB, save full dict
            final_kbs.append(kb)

    # Serialize to JSON or simple comma-separated list
    if all(isinstance(x, str) for x in final_kbs):
        kbs_value = ",".join(final_kbs)
    else:
        # Use Pydantic's serialization
        kbs_value = TypeAdapter(List[Union[str, KBDefinition]]).dump_json(final_kbs).decode()

    env = {"MCP_KNOWLEDGE_BASES": kbs_value}

    if api_key:
        env["GEMINI_API_KEY"] = api_key
    elif os.environ.get("GEMINI_API_KEY"):
        env["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY")

    if github_token:
        env["GITHUB_TOKEN"] = github_token
    elif os.environ.get("GITHUB_TOKEN"):
        env["GITHUB_TOKEN"] = os.environ.get("GITHUB_TOKEN")

    # Construct uvx command
    if local_path:
        # Resolve the absolute path to the package root
        pkg_spec = str(Path(local_path).resolve())
        if not (Path(pkg_spec) / "pyproject.toml").exists():
            # Try to find tools/adk_knowledge_ext within the path
            if (Path(pkg_spec) / "tools" / "adk_knowledge_ext").exists():
                pkg_spec = str(Path(pkg_spec) / "tools" / "adk_knowledge_ext")
    else:
        pkg_spec = "git+https://github.com/ivanmkc/agent-generator.git@mcp_server#subdirectory=tools/adk_knowledge_ext"

    return McpServerConfig(
        command="uvx",
        args=["--from", pkg_spec, "codebase-knowledge-mcp"],
        env=env,
    )


def _is_mcp_configured(ide_name: str, ide_info: IdeConfig) -> bool:
    """Checks if the MCP server is already configured in a specific IDE.
    
    Args:
        ide_name (str): Name of the IDE.
        ide_info (IdeConfig): Configuration metadata for the IDE.
        
    Returns:
        bool: True if the server is found in the IDE's configuration.
    """
    config_method = ide_info.config_method
    if config_method == "cli":
        cli_cmd = ide_info.cli_command
        try:
            result = subprocess.run([cli_cmd, "mcp", "list"], capture_output=True, text=True)
            # Check both stdout and stderr (Gemini CLI prints to stderr)
            output = result.stdout + result.stderr
            return MCP_SERVER_NAME in output
        except FileNotFoundError:
            return False
    else:
        config_path = ide_info.config_path
        if config_path and config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    servers = config.get(ide_info.config_key or "mcpServers", {})
                    return MCP_SERVER_NAME in servers
            except (json.JSONDecodeError, KeyError):
                return False
        return False


def _configure_ide(
    ide_name: str, ide_info: IdeConfig, mcp_config: McpServerConfig
) -> None:
    """Configures the MCP server in a specific IDE.

    Args:
        ide_name (str): Name of the IDE.
        ide_info (IdeConfig): Configuration metadata for the IDE.
        mcp_config (McpServerConfig): The server configuration to apply.
    """
    config_method = ide_info.config_method
    if config_method == "cli":
        _configure_cli_based(ide_name, ide_info, mcp_config)
    else:
        _configure_ide_json(ide_info, mcp_config)


def _configure_cli_based(
    ide_name: str, ide_info: IdeConfig, mcp_config: McpServerConfig
) -> None:
    """Uses a CLI tool to configure the MCP server.

    Args:
        ide_name (str): Name of the IDE.
        ide_info (IdeConfig): Configuration metadata for the IDE.
        mcp_config (McpServerConfig): The server configuration to apply.
    """
    cli_cmd = ide_info.cli_command
    scope_flag = ide_info.cli_scope_flag
    scope_value = ide_info.cli_scope_value
    separator_style = ide_info.cli_separator

    # Remove existing
    try:
        if scope_flag:
            for scope in ["user", "project", "local"]:
                subprocess.run(
                    [cli_cmd, "mcp", "remove", MCP_SERVER_NAME, scope_flag, scope],
                    capture_output=True,
                )
        else:
            subprocess.run(
                [cli_cmd, "mcp", "remove", MCP_SERVER_NAME], capture_output=True
            )
    except FileNotFoundError:
        pass  # CLI tool might not be in PATH even if folder exists

    # Add
    cmd = [cli_cmd, "mcp", "add"]
    if scope_flag:
        cmd.extend([scope_flag, scope_value])
    cmd.append(MCP_SERVER_NAME)

    env_args = []
    for k, v in mcp_config.env.items():
        env_args.append(f"{k}={v}")

    # We use `env` as the command to set variables
    # cmd: env VAR=VAL uvx ...

    final_command = "env"
    final_args = env_args + [mcp_config.command] + mcp_config.args

    if separator_style == "before_command":
        # Claude: mcp add name -- env VAR=VAL ...
        cmd.append("--")
        cmd.append(final_command)
        cmd.extend(final_args)
    else:
        # Gemini: mcp add name env -- VAR=VAL ...
        cmd.append(final_command)
        cmd.append("--")
        cmd.extend(final_args)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{cli_cmd} mcp add failed: {result.stderr}")


def _configure_ide_json(ide_info: IdeConfig, mcp_config: McpServerConfig) -> None:
    """Updates a JSON configuration file to include the MCP server.

    Args:
        ide_info (IdeConfig): Configuration metadata for the IDE.
        mcp_config (McpServerConfig): The server configuration to apply.
    """
    config_path = ide_info.config_path
    config_key = ide_info.config_key
    
    # Ensure dir exists
    if not config_path.parent.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        # Create backup
        backup_path = config_path.with_name(config_path.name + ".bak")
        try:
            shutil.copy2(config_path, backup_path)
        except Exception as e:
            console.print(f"   [yellow]Warning: Failed to backup config: {e}[/yellow]")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            pass

    if config_key not in config:
        config[config_key] = {}

    config[config_key][MCP_SERVER_NAME] = mcp_config.model_dump()

    # Automatically add system instructions to Gemini CLI context
    start_instruction = ide_info.start_instruction

    if (
        "gemini" in start_instruction.lower()
        or "antigravity" in start_instruction.lower()
    ):
        # Get KBs from config to find repo names
        try:
            kbs_raw = mcp_config.env.get("MCP_KNOWLEDGE_BASES")

            # Robust parsing of KBs (JSON list or comma-separated string) using TypeAdapter
            kb_list_adapter = TypeAdapter(List[Union[str, KBDefinition]])
            kbs_input: List[Union[str, KBDefinition]] = []
            if kbs_raw:
                if kbs_raw.startswith("["):
                    kbs_input = kb_list_adapter.validate_json(kbs_raw)
                else:
                    kbs_input = [x.strip() for x in kbs_raw.split(",") if x.strip()]

            # Load Registry for enrichment of string-only IDs
            import yaml

            registry_path = Path(__file__).parent / "registry.yaml"
            registry = {}
            if registry_path.exists():
                try:
                    registry = yaml.safe_load(registry_path.read_text())
                except Exception:
                    pass

            kbs: List[KBDefinition] = []
            for item in kbs_input:
                if isinstance(item, str):
                    # Enrich from registry
                    match_found = False
                    if "repositories" in registry:
                        for repo_id, meta in registry["repositories"].items():
                            if "@" in item:
                                rid, ver = item.split("@", 1)
                                if rid == repo_id and ver in meta.get("versions", {}):
                                    v_meta = meta["versions"][ver]
                                    kbs.append(
                                        KBDefinition(
                                            id=item,
                                            repo_url=meta["repo_url"],
                                            version=ver,
                                            description=v_meta.get("description")
                                            or meta.get("description"),
                                        )
                                    )
                                    match_found = True
                                    break
                            elif item == repo_id:
                                ver = meta.get("default_version")
                                v_meta = meta.get("versions", {}).get(ver, {})
                                kbs.append(
                                    KBDefinition(
                                        id=item,
                                        repo_url=meta["repo_url"],
                                        version=ver,
                                        description=v_meta.get("description")
                                        or meta.get("description"),
                                    )
                                )
                                match_found = True
                                break

                    if not match_found:
                        # Fallback for unknown strings
                        kbs.append(
                            KBDefinition(id=item, repo_url="Unknown", version="Unknown")
                        )
                else:
                    kbs.append(item)

            instr_paths = []

            # Prepare Registry String
            # Group by repo_url to create compact listing
            from collections import defaultdict

            repos = defaultdict(list)
            for kb_def in kbs:
                repos[kb_def.repo_url].append(kb_def)

            registry_lines = []
            for repo_url, versions in repos.items():
                v0 = versions[0]
                desc = v0.description or f"Codebase: {repo_url}"
                # Derive repo name for display (e.g. google/adk-python)
                repo_id = "Unknown Repo"
                if "@" in v0.id:
                    repo_id = v0.id.split("@")[0]
                elif v0.id:
                    repo_id = v0.id
                else:
                    repo_id = repo_url.split("/")[-1].replace(".git", "")

                registry_lines.append(f"*   `{repo_id}` | {desc}")
                for v in versions:
                    registry_lines.append(f"    *   Version: `{v.version}`")
                    registry_lines.append(
                        f"    *   *Usage:* `list_modules(kb_id=\"{v.id}\", ...)`"
                    )

            registry_str = "\n".join(registry_lines)
            
            # Find Template
            bundled_instr = Path(__file__).parent / "data" / "INSTRUCTIONS.md"
            source_template = Path(__file__).parent.parent.parent / "INSTRUCTIONS.template.md"
            
            template_content = ""
            if source_template.exists():
                template_content = source_template.read_text()
            elif bundled_instr.exists():
                template_content = bundled_instr.read_text()

            if template_content:
                # Fallback: If no KBs selected, generate a generic instruction using registry
                if not kbs:
                    registry_path = Path(__file__).parent / "registry.yaml"
                    if registry_path.exists():
                        try:
                            data = yaml.safe_load(registry_path.read_text())
                            fallback_lines = []
                            if "repositories" in data:
                                for repo_id, meta in data["repositories"].items():
                                    desc = meta.get("description", f"Codebase: {meta['repo_url']}")
                                    fallback_lines.append(f"*   `{repo_id}` | {desc}")
                                    for ver, v_meta in meta.get("versions", {}).items():
                                        kb_id = f"{repo_id}@{ver}"
                                        fallback_lines.append(f"    *   Version: `{ver}`")
                                        fallback_lines.append(f"    *   *Usage:* `list_modules(kb_id=\"{kb_id}\", ...)`")
                            
                            if fallback_lines:
                                registry_str = "\n".join(fallback_lines)
                        except Exception:
                            pass
                
                # Regenerate registry string with potentially updated map (fallback case)
                # registry_str is already string now, no yaml dump needed if fallback used or normal path used string.
                # But wait, normal path sets registry_str. Fallback path sets registry_str.
                # We need to ensure we don't double dump or overwrite if kbs existed.
                
                # If kbs existed, registry_str is set. If not, fallback sets it.
                # No need to do yaml.safe_dump here anymore.
                pass

                # Preferred path: .gemini/instructions/ in current workspace
                # Fallback: ~/.mcp_cache/instructions/
                local_gemini = Path.cwd() / ".gemini"
                instr_filename = "KNOWLEDGE_MCP_SERVER_INSTRUCTION.md"
                
                # Check if we are in the home directory
                try:
                    is_home = Path.cwd().resolve().samefile(Path.home().resolve())
                except Exception:
                    is_home = (Path.cwd().resolve() == Path.home().resolve())
                
                # If .gemini exists OR we are in a workspace (not home), use local .gemini
                if local_gemini.exists() or not is_home:
                    instr_path = local_gemini / "instructions" / instr_filename
                else:
                    instr_path = Path.home() / ".mcp_cache" / "instructions" / instr_filename
                    
                instr_path.parent.mkdir(parents=True, exist_ok=True)
                
                content = template_content.replace("{{KB_REGISTRY}}", registry_str)
                instr_path.write_text(content)
                
                # Use relative path if within workspace
                try:
                    rel_p = instr_path.relative_to(Path.cwd())
                    instr_paths.append(str(rel_p))
                except ValueError:
                    instr_paths.append(str(instr_path))
            
            if instr_paths:
                if "context" not in config:
                    config["context"] = {}
                
                existing_files = config["context"].get("fileName", [])
                existing_dirs = config["context"].get("includeDirectories", [])
                
                for p in instr_paths:
                    if p not in existing_files:
                        existing_files.append(p)
                    
                    # Ensure parent dir is included
                    try:
                        parent_dir = str(Path(p).parent)
                        if parent_dir not in existing_dirs:
                            existing_dirs.append(parent_dir)
                    except Exception:
                        pass
                
                config["context"]["includeDirectories"] = existing_dirs
                # Enable loading
                config["context"]["loadMemoryFromIncludeDirectories"] = True
                
                # Deduplicate and add files
                current_files = config["context"].get("fileName", [])
                # Normalize existing for comparison
                existing_abs = set()
                for f in current_files:
                    try:
                        existing_abs.add(str(Path(f).resolve()))
                    except Exception:
                        existing_abs.add(str(f))
                
                for p in instr_paths:
                    try:
                        p_abs = str(Path(p).resolve())
                        if p_abs not in existing_abs:
                            current_files.append(p)
                            existing_abs.add(p_abs)
                    except Exception:
                        if p not in current_files:
                            current_files.append(p)
                
                config["context"]["fileName"] = current_files
        except Exception:
            pass

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _remove_mcp_config(ide_name: str, ide_info: IdeConfig) -> None:
    """Internal helper to remove MCP server configuration.
    
    Args:
        ide_name (str): Name of the IDE.
        ide_info (IdeConfig): Configuration metadata for the IDE.
    """
    config_method = ide_info.config_method
    if config_method == "cli":
        cli_cmd = ide_info.cli_command
        scope_flag = ide_info.cli_scope_flag
        if scope_flag:
            for scope in ["user", "project", "local"]:
                subprocess.run([cli_cmd, "mcp", "remove", MCP_SERVER_NAME, scope_flag, scope], capture_output=True)
        else:
            subprocess.run([cli_cmd, "mcp", "remove", MCP_SERVER_NAME], capture_output=True)
    else:
        config_path = ide_info.config_path
        config_key = ide_info.config_key
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    config = json.load(f)
                except json.JSONDecodeError:
                    return
            
            if config_key in config and MCP_SERVER_NAME in config[config_key]:
                del config[config_key][MCP_SERVER_NAME]
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)

def main():
    """Main entry point for the CLI."""
    cli()

if __name__ == "__main__":
    main()
