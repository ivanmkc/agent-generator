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

console = Console()

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
@click.option("--repo-url", help="Target repository URL (e.g. https://github.com/google/adk-python.git)")
@click.option("--version", default="main", help="Target version/branch (default: main)")
@click.option("--api-key", help="Gemini API Key (optional, for semantic search)")
@click.option("--index-url", help="Custom PyPI index URL (e.g. https://pypi.org/simple) for uvx")
@click.option("--knowledge-index-url", help="Direct URL or file path to the knowledge index YAML (overrides registry lookup)")
@click.option("--local", is_flag=True, help="Use the local source directory for the MCP server (development mode)")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
def setup(repo_url: Optional[str], version: str, api_key: Optional[str], index_url: Optional[str], knowledge_index_url: Optional[str], local: bool, force: bool):
    """Auto-configure this MCP server in your coding agents."""
    
    selected_kbs = []

    # 1. Resolve Selection
    if repo_url:
        # Direct CLI usage
        selected_kbs.append({
            "repo_url": repo_url,
            "version": version,
            "index_url": knowledge_index_url
        })
    else:
        # Interactive Mode
        registry_path = Path(__file__).parent / "registry.yaml"
        available_options = []
        if registry_path.exists():
            try:
                registry = yaml.safe_load(registry_path.read_text())
                for r_url, versions in registry.items():
                    for ver, idx_url in versions.items():
                        available_options.append({
                            "repo_url": r_url,
                            "version": ver,
                            "index_url": idx_url,
                            "label": f"{r_url} ({ver})"
                        })
            except Exception:
                pass

        if available_options:
            console.print("\n[bold]Available Knowledge Bases:[/bold]")
            for i, opt in enumerate(available_options):
                console.print(f"[{i+1}] {opt['label']}")
            console.print("[0] Enter custom repository URL")
            
            selection_input = Prompt.ask("\nSelect one or more (comma-separated, e.g. 1, 2) or 0 for custom")
            selected_indices = [int(x.strip()) for x in selection_input.split(",") if x.strip().isdigit()]
            
            # Add Registry Selections
            for idx in selected_indices:
                if 1 <= idx <= len(available_options):
                    opt = available_options[idx-1]
                    # Clean up label before saving
                    selected_kbs.append({
                        "repo_url": opt["repo_url"],
                        "version": opt["version"],
                        "index_url": opt["index_url"]
                    })
            
            # Add Custom Selection
            if 0 in selected_indices or not selected_kbs:
                custom_url = Prompt.ask("Enter the Custom Repository URL")
                selected_kbs.append({
                    "repo_url": custom_url,
                    "version": "main", # Default for custom
                    "index_url": None
                })
        else:
            # Fallback if registry missing
            repo_url = Prompt.ask("Enter the Target Repository URL")
            selected_kbs.append({
                "repo_url": repo_url,
                "version": version,
                "index_url": knowledge_index_url
            })

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
        console.print("\n[bold]Configure MCP for:[/bold]")
        for ide_name in detected_ides:
            default_val = not configured_status.get(ide_name, False)
            if ask_confirm(f"   {ide_name}", default=default_val):
                selected_ides[ide_name] = detected_ides[ide_name]

    if not selected_ides:
        console.print("No IDEs selected.")
        return

    # Generate Config
    mcp_config = _generate_mcp_config(selected_kbs, api_key, index_url, local)

    # Configure
    console.print("\n[bold]Applying configuration...[/bold]")
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


def _generate_mcp_config(selected_kbs: List[Dict[str, str]], api_key: Optional[str], index_url: Optional[str] = None, local: bool = False) -> dict:
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
             repo_map = registry.get(kb["repo_url"], {})
             kb["index_url"] = repo_map.get(kb["version"])

    env = {
        "MCP_KNOWLEDGE_BASES": json.dumps(selected_kbs)
    }
    
    if api_key:
        env["GEMINI_API_KEY"] = api_key
    elif os.environ.get("GEMINI_API_KEY"):
        env["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY")

    # Construct uvx command
    if local:
        # Resolve the absolute path to the package root (tools/adk_knowledge_ext)
        # We assume this script is running from within the package or we use CWD if valid
        # A safer bet for development is assuming the user runs it from the repo root or passing CWD
        # Ideally, we find the path relative to THIS file if it's in the src tree
        # manage_mcp.py is in src/adk_knowledge_ext/manage_mcp.py
        # root is 3 levels up: src/adk_knowledge_ext/ -> src/ -> tools/adk_knowledge_ext
        
        # But this file might be installed in site-packages!
        # If installed, we can't infer the source path easily.
        # So we assume CWD is the project root if --local is passed.
        pkg_spec = os.getcwd()
        if not (Path(pkg_spec) / "pyproject.toml").exists():
             # Try to find tools/adk_knowledge_ext
             if (Path(pkg_spec) / "tools" / "adk_knowledge_ext").exists():
                 pkg_spec = str(Path(pkg_spec) / "tools" / "adk_knowledge_ext")
    else:
        pkg_spec = "git+https://github.com/ivanmkc/agent-generator.git@mcp_server#subdirectory=tools/adk_knowledge_ext"
    
    args = []
    if index_url:
        args.extend(["--index-url", index_url])
        
    args.extend([
        "--from",
        pkg_spec,
        "codebase-knowledge-mcp"
    ])
    
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
            
            # Prepare Registry String
            registry_str = yaml.safe_dump(kbs, sort_keys=False)
            
            # Find Template
            bundled_instr = Path(__file__).parent / "data" / "INSTRUCTIONS.md"
            source_template = Path(__file__).parent.parent.parent / "INSTRUCTIONS.template.md"
            
            template_content = ""
            if source_template.exists():
                template_content = source_template.read_text()
            elif bundled_instr.exists():
                template_content = bundled_instr.read_text()

            for kb in kbs:
                repo_url = kb["repo_url"]
                version = kb["version"]
                repo_name = repo_url.split("/")[-1].replace(".git", "")
                kb_id = f"{repo_name}-{version}" if version != "main" else repo_name
                
                # Preferred path: .gemini/instructions/ in current workspace
                # Fallback: ~/.mcp_cache/instructions/
                local_gemini = Path.cwd() / ".gemini"
                if local_gemini.exists():
                    instr_path = local_gemini / "instructions" / f"{repo_name}.md"
                else:
                    instr_path = Path.home() / ".mcp_cache" / "instructions" / f"{repo_name}.md"
                    
                instr_path.parent.mkdir(parents=True, exist_ok=True)
                
                if template_content:
                    content = template_content.replace("{{TARGET_REPO_URL}}", repo_url)
                    content = content.replace("{{TARGET_VERSION}}", version)
                    content = content.replace("{{KB_REGISTRY}}", registry_str)
                    content = content.replace("{{CURRENT_KB_ID}}", kb_id)
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
                
                config["context"]["fileName"] = existing_files
                config["context"]["includeDirectories"] = existing_dirs
                # Enable loading
                config["context"]["loadMemoryFromIncludeDirectories"] = True
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