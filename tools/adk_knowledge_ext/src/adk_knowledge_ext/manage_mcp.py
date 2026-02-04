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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Any, List

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from pydantic import BaseModel

# Import reader for pre-cloning
try:
    from .reader import SourceReader
except ImportError:
    # If running as script
    from adk_knowledge_ext.reader import SourceReader

console = Console()

class RegistryEntry(BaseModel):
    """Model for a Knowledge Base registry entry."""
    id: str
    repo_url: str
    version: str
    index_url: Optional[str] = None
    description: Optional[str] = None
    
    @property
    def label(self) -> str:
        return f"{self.repo_url} ({self.version})"

def ask_confirm(question: str, default: bool = True) -> bool:
    """Case-insensitive confirmation prompt."""
    choices = "[Y/n]" if default else "[y/N]"
    resp = Prompt.ask(f"{question} {choices}", default="y" if default else "n", show_default=False)
    return resp.lower().startswith("y")

MCP_SERVER_NAME = "codebase-knowledge"

def _get_platform_config_path(app_name: str, config_file: str) -> Path:
    """Helper to determine config path based on OS."""
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
        
    return Path.home() / f".{app_name.lower().replace(' ', '-')}" / config_file


# IDE configuration - how to detect, configure, and start each IDE
IDE_CONFIGS = {
    "Claude Code": {
        "detect_path": Path.home() / ".claude",
        "config_method": "cli",
        "cli_command": "claude",
        "cli_scope_flag": "--scope",
        "cli_scope_value": "user",
        # Claude: cmd -- <command> <args...>
        "cli_separator": "before_command",
        "start_instruction": "Run [cyan]claude[/cyan] in your terminal",
    },
    "Gemini CLI": {
        "detect_path": Path.home() / ".gemini",
        "config_method": "json",
        "config_path": Path.home() / ".gemini" / "settings.json",
        "config_key": "mcpServers",
        "start_instruction": "Run [cyan]gemini[/cyan] in your terminal",
    },
    "Cursor": {
        "detect_path": Path.home() / ".cursor",
        "config_method": "json",
        "config_path": Path.home() / ".cursor" / "mcp.json",
        "config_key": "mcpServers",
        "start_instruction": "Open [cyan]Cursor[/cyan] app",
    },
    "Windsurf": {
        "detect_path": Path.home() / ".codeium" / "windsurf",
        "config_method": "json",
        "config_path": Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
        "config_key": "mcpServers",
        "start_instruction": "Open [cyan]Windsurf[/cyan] app",
    },
    "Antigravity": {
        "detect_path": Path.home() / ".gemini" / "antigravity",
        "config_method": "json",
        "config_path": Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        "config_key": "mcpServers",
        "start_instruction": "Open [cyan]Antigravity[/cyan] IDE",
    },
    "Codex": {
        "detect_path": Path.home() / ".codex",
        "config_method": "cli",
        "cli_command": "codex",
        "cli_scope_flag": None,  # Codex doesn't use scope flags
        "cli_scope_value": None,
        "cli_separator": "before_command",
        "start_instruction": "Run [cyan]codex[/cyan] in your terminal",
    },
    "Roo Code": {
        "detect_path": Path.home() / ".roo-code",
        "config_method": "json",
        "config_path": Path.home() / ".roo-code" / "mcp.json",
        "config_key": "mcpServers",
        "start_instruction": "Open [cyan]Roo Code[/cyan] in VS Code",
    },
}

@click.group()
def cli():
    """Manage the Codebase Knowledge MCP server configuration."""
    pass

@cli.command()
@click.option("--kb-ids", help="Comma-separated list of Knowledge Base IDs to configure (e.g. adk-python-v1.20.0)")
@click.option("--api-key", help="Gemini API Key (optional, for semantic search)")
@click.option("--local", "local_path", help="Use local source directory for the MCP server. Optionally provide path to the package root.")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option("--quiet", "-q", is_flag=True, help="Quiet mode (implies --force)")
def setup(kb_ids: Optional[str], api_key: Optional[str], local_path: Optional[str], force: bool, quiet: bool):
    """Auto-configure this MCP server in your coding agents."""
    
    local = local_path is not None
    # Quiet implies force
    if quiet:
        force = True
        
    selected_kbs = []

    # Load Registry
    registry_path = Path(__file__).parent / "registry.yaml"
    registry_options: List[RegistryEntry] = []
    if registry_path.exists():
        try:
            registry_data = yaml.safe_load(registry_path.read_text())
            for kb_id, meta in registry_data.items():
                registry_options.append(RegistryEntry(
                    id=kb_id,
                    repo_url=meta["repo_url"],
                    version=meta["version"],
                    index_url=meta.get("index_url"),
                    description=meta.get("description")
                ))
        except Exception:
            pass

    # 1. Resolve Selection
    if kb_ids:
        # Resolve IDs from registry
        requested_ids = [x.strip() for x in kb_ids.split(",") if x.strip()]
        for rid in requested_ids:
            match = next((opt for opt in registry_options if opt.id == rid), None)
            if match:
                selected_kbs.append({
                    "repo_url": match.repo_url,
                    "version": match.version,
                    "index_url": match.index_url,
                    "description": match.description
                })
            else:
                console.print(f"[yellow]Warning: KB ID '{rid}' not found in registry.[/yellow]")
    else:
        # Interactive Mode (unless quiet)
        if quiet:
            # In quiet mode without kb_ids, we assume empty selection (using bundled registry only)
            pass
        elif registry_options:
            console.print("\n[bold]Available Knowledge Bases:[/bold]")
            for i, opt in enumerate(registry_options):
                desc_suffix = f" - {opt.description}" if opt.description else ""
                console.print(f"[{i+1}] {opt.id}: {opt.label}{desc_suffix}")
            
            selection_input = Prompt.ask("\nSelect one or more (comma-separated indices or IDs)")
            # Handle both indices and string IDs
            parts = [x.strip() for x in selection_input.split(",")]
            for p in parts:
                if p.isdigit():
                    idx = int(p)
                    if 1 <= idx <= len(registry_options):
                         match = registry_options[idx-1]
                         selected_kbs.append({
                            "repo_url": match.repo_url,
                            "version": match.version,
                            "index_url": match.index_url,
                            "description": match.description
                        })
                else:
                    match = next((opt for opt in registry_options if opt.id == p), None)
                    if match:
                         selected_kbs.append({
                            "repo_url": match.repo_url,
                            "version": match.version,
                            "index_url": match.index_url,
                            "description": match.description
                        })

        else:
            # Fallback if registry missing
            console.print("[red]Registry missing and no KB IDs provided.[/red]")
            return

    # Pre-load/Clone Repositories
    if selected_kbs:
        console.print("\n[bold]Pre-loading Knowledge Bases...[/bold]")
        for kb in selected_kbs:
            try:
                reader = SourceReader(kb["repo_url"], kb["version"])
                console.print(f"   Using {kb['repo_url']}...")
                # SourceReader.__init__ triggers clone if missing.
            except Exception as e:
                console.print(f"   [yellow]Warning: Failed to pre-clone {kb['repo_url']}: {e}[/yellow]")

    # Optional API Key
    if not force and not api_key and not os.environ.get("GEMINI_API_KEY"):
        if ask_confirm("Do you have a Gemini API Key? (Required for semantic search)", default=False):
            api_key = Prompt.ask("Enter Gemini API Key", password=True)

    console.print()
    console.print(
        Panel(
            "[bold]🚀 Codebase Knowledge MCP Setup[/bold]\n\n" +
            "\n".join([f"- {kb['repo_url']} ({kb['version']})" for kb in selected_kbs]),
            border_style="blue",
        )
    )

    # Detect IDEs
    console.print("[bold]🔍 Detecting installed coding agents...[/bold]")
    
    detected_ides = {}
    for ide_name, ide_info in IDE_CONFIGS.items():
        is_installed = False
        
        # Check based on method
        if ide_info["config_method"] == "cli":
            # For CLI, verify binary is in PATH
            if shutil.which(ide_info["cli_command"]):
                is_installed = True
            elif ide_info["detect_path"].exists():
                 # Fallback: Folder exists but not in PATH
                 # We mark as False to avoid 'No such file' error, but we'll show a warning
                 is_installed = False
        else:
            # For JSON, just check dir existence
            if ide_info["detect_path"].exists():
                is_installed = True
                
        if is_installed:
            detected_ides[ide_name] = ide_info

    configured_status = {}
    def check_configured(ide_name: str) -> tuple[str, bool]:
        return ide_name, _is_mcp_configured(ide_name, detected_ides[ide_name])

    if detected_ides:
        with ThreadPoolExecutor(max_workers=len(detected_ides)) as executor:
            results = executor.map(check_configured, detected_ides.keys())
            configured_status = dict(results)

    # Display results
    for ide_name, ide_info in IDE_CONFIGS.items():
        detect_path = ide_info["detect_path"]
        if ide_name in detected_ides:
            status = "[green](configured)[/green]" if configured_status.get(ide_name) else ""
            console.print(f"   ✓ {ide_name:<15} [dim]{detect_path}[/dim] {status}")
        else:
            # Check if it was a CLI tool that failed verification
            if ide_info["config_method"] == "cli" and ide_info["detect_path"].exists():
                console.print(f"   [yellow]! {ide_name:<15} (config found at {detect_path}, but '{ide_info['cli_command']}' not in PATH)[/yellow]")
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

    # Configure
    console.print("\n[bold]Applying configuration...[/bold]")
    # Resolve local path if provided as a flag but empty, or use the provided string
    resolved_local_path = None
    if local:
        # If run as --local (flag only), local_path might be empty string or True depending on click config, 
        # but here we changed it to a non-flag option. If user wants current dir, they can pass '.' or we handle None.
        # Actually, let's make it robust:
        resolved_local_path = local_path if local_path else "."

    mcp_config = _generate_mcp_config(selected_kbs, api_key, resolved_local_path)

    for ide_name, ide_info in selected_ides.items():
        try:
            _configure_ide(ide_name, ide_info, mcp_config)
            console.print(f"✅ {ide_name} configured")
        except Exception as e:
            console.print(f"[red]❌ {ide_name} failed: {e}[/red]")

    console.print("\n[bold green]🎉 Setup complete![/bold green]")


@cli.command()
def remove():
    """Remove this MCP server configuration from coding agents."""
    console.print("\n[bold]🗑️  Codebase Knowledge MCP Remove[/bold]\n")

    configured_ides = {}
    for ide_name, ide_info in IDE_CONFIGS.items():
        # For CLI tools, we need the binary to check config (mcp list)
        is_runnable = True
        if ide_info["config_method"] == "cli" and not shutil.which(ide_info["cli_command"]):
            is_runnable = False
            
        if ide_info["detect_path"].exists() and is_runnable and _is_mcp_configured(ide_name, ide_info):
            configured_ides[ide_name] = ide_info
            console.print(f"   ✓ {ide_name:<15} [green]configured[/green]")

    if not configured_ides:
        console.print("[yellow]No coding agents have this MCP configured.[/yellow]")
        return

    selected_ides = {}
    console.print("\n[bold]Remove from:[/bold]")
    for ide_name in configured_ides:
        if ask_confirm(f"   {ide_name}", default=True):
            selected_ides[ide_name] = configured_ides[ide_name]

    if not selected_ides:
        return

    for ide_name, ide_info in selected_ides.items():
        try:
            _remove_mcp_config(ide_name, ide_info)
            console.print(f"✅ {ide_name} - removed")
        except Exception as e:
            console.print(f"[red]❌ {ide_name} failed: {e}[/red]")


def _generate_mcp_config(selected_kbs: List[Dict[str, str]], api_key: Optional[str], local_path: Optional[str] = None) -> dict:
    """Generate the MCP server configuration."""
    
    # Enrich KBs with registry info if index_url missing
    import yaml
    registry_path = Path(__file__).parent / "registry.yaml"
    registry = {}
    if registry_path.exists():
        try:
            registry = yaml.safe_load(registry_path.read_text())
        except Exception:
            pass

    for kb in selected_kbs:
        if not kb.get("index_url"):
             # Try to find matching entry in flattened registry
             # We match on repo_url AND version
             for kb_id, meta in registry.items():
                 if meta.get("repo_url") == kb["repo_url"] and meta.get("version") == kb["version"]:
                     kb["index_url"] = meta.get("index_url")
                     if not kb.get("description"):
                         kb["description"] = meta.get("description")
                     break

    env = {
        "MCP_KNOWLEDGE_BASES": json.dumps(selected_kbs)
    }
    
    if api_key:
        env["GEMINI_API_KEY"] = api_key
    elif os.environ.get("GEMINI_API_KEY"):
        env["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY")

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
    
    args = [
        "--from",
        pkg_spec,
        "codebase-knowledge-mcp"
    ]
    
    return {
        "command": "uvx",
        "args": args,
        "env": env
    }


def _is_mcp_configured(ide_name: str, ide_info: dict) -> bool:
    config_method = ide_info.get("config_method", "json")
    if config_method == "cli":
        cli_cmd = ide_info["cli_command"]
        try:
            result = subprocess.run([cli_cmd, "mcp", "list"], capture_output=True, text=True)
            # Check both stdout and stderr (Gemini CLI prints to stderr)
            output = result.stdout + result.stderr
            return MCP_SERVER_NAME in output
        except FileNotFoundError:
            return False
    else:
        config_path = ide_info.get("config_path")
        if config_path and config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    servers = config.get(ide_info.get("config_key", "mcpServers"), {})
                    return MCP_SERVER_NAME in servers
            except (json.JSONDecodeError, KeyError):
                return False
        return False


def _configure_ide(ide_name: str, ide_info: dict, mcp_config: dict) -> None:
    config_method = ide_info.get("config_method", "json")
    if config_method == "cli":
        _configure_cli_based(ide_name, ide_info, mcp_config)
    else:
        _configure_ide_json(ide_info, mcp_config)


def _configure_cli_based(ide_name: str, ide_info: dict, mcp_config: dict) -> None:
    cli_cmd = ide_info["cli_command"]
    scope_flag = ide_info.get("cli_scope_flag")
    scope_value = ide_info.get("cli_scope_value")
    separator_style = ide_info.get("cli_separator", "before_command")

    # Remove existing
    try:
        if scope_flag:
            for scope in ["user", "project", "local"]:
                subprocess.run([cli_cmd, "mcp", "remove", MCP_SERVER_NAME, scope_flag, scope], capture_output=True)
        else:
            subprocess.run([cli_cmd, "mcp", "remove", MCP_SERVER_NAME], capture_output=True)
    except FileNotFoundError:
        pass # CLI tool might not be in PATH even if folder exists

    # Add
    cmd = [cli_cmd, "mcp", "add"]
    if scope_flag:
        cmd.extend([scope_flag, scope_value])
    cmd.append(MCP_SERVER_NAME)

    
    env_args = []
    if "env" in mcp_config:
        for k, v in mcp_config["env"].items():
            env_args.append(f"{k}={v}")
            
    # We use `env` as the command to set variables
    # cmd: env VAR=VAL uvx ...
    
    final_command = "env"
    final_args = env_args + [mcp_config["command"]] + mcp_config["args"]
    
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


def _configure_ide_json(ide_info: dict, mcp_config: dict) -> None:
    config_path = ide_info["config_path"]
    config_key = ide_info["config_key"]
    
    # Ensure dir exists
    if not config_path.parent.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            pass

    if config_key not in config:
        config[config_key] = {}

    config[config_key][MCP_SERVER_NAME] = mcp_config

    # Automatically add system instructions to Gemini CLI context
    start_instruction = ide_info.get("start_instruction", "")
    
    if "gemini" in start_instruction.lower() or "antigravity" in start_instruction.lower():
        # Get KBs from config to find repo names
        try:
            kbs_json = mcp_config["env"]["MCP_KNOWLEDGE_BASES"]
            kbs = json.loads(kbs_json)
            instr_paths = []
            
            # Prepare Registry String: {kb_id: description}
            registry_map = {}
            for kb in kbs:
                r_url = kb["repo_url"]
                ver = kb["version"]
                r_name = r_url.split("/")[-1].replace(".git", "")
                k_id = f"{r_name}-{ver}" if ver != "main" else r_name
                
                desc = kb.get("description")
                if not desc:
                    desc = f"Codebase: {r_url} (version: {ver})"
                registry_map[k_id] = desc
            
            registry_str = yaml.safe_dump(registry_map, sort_keys=False, width=1000).strip()
            
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
                            registry_data = yaml.safe_load(registry_path.read_text())
                            # Construct synthetic KB list for instruction generation purposes
                            # We use the first one as "current" or just generic
                            # Actually, we can generate one file listing all.
                            
                            # Update registry map for all
                            for kid, meta in registry_data.items():
                                registry_map[kid] = meta.get("description", f"Codebase: {meta['repo_url']}")
                            
                            registry_str = yaml.safe_dump(registry_map, sort_keys=False, width=1000).strip()
                            
                            # Fake a KB for the loop to run once
                            kbs_to_process = [{
                                "repo_url": "dynamic",
                                "version": "dynamic",
                                "kb_id": "registry_catalog" 
                            }]
                        except Exception:
                            kbs_to_process = []
                    else:
                        kbs_to_process = []
                else:
                    kbs_to_process = kbs

                for kb in kbs_to_process:
                    # Determine ID
                    if "kb_id" in kb:
                        kb_id = kb["kb_id"]
                    else:
                        r_url = kb["repo_url"]
                        ver = kb["version"]
                        r_name = r_url.split("/")[-1].replace(".git", "")
                        kb_id = f"{r_name}-{ver}" if ver != "main" else r_name
                    
                    # Preferred path: .gemini/instructions/ in current workspace
                    # Fallback: ~/.mcp_cache/instructions/
                    local_gemini = Path.cwd() / ".gemini"
                    instr_filename = f"INSTRUCTION_{kb_id}.md"
                    
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


def _remove_mcp_config(ide_name: str, ide_info: dict) -> None:
    config_method = ide_info.get("config_method", "json")
    if config_method == "cli":
        cli_cmd = ide_info["cli_command"]
        scope_flag = ide_info.get("cli_scope_flag")
        if scope_flag:
            for scope in ["user", "project", "local"]:
                subprocess.run([cli_cmd, "mcp", "remove", MCP_SERVER_NAME, scope_flag, scope], capture_output=True)
        else:
            subprocess.run([cli_cmd, "mcp", "remove", MCP_SERVER_NAME], capture_output=True)
    else:
        config_path = ide_info["config_path"]
        config_key = ide_info["config_key"]
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
    cli()

if __name__ == "__main__":
    main()