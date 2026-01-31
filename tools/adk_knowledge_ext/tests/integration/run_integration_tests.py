"""
Main integration test runner for the Codebase Knowledge MCP server.

This script orchestrates multiple end-to-end test scenarios using Podman containers.
It verifies:
1. Manual installation and execution via uvx.
2. Extension-style installation and configuration discovery.
3. Resilience against invalid repository versions.
4. Resilience against missing index files.
5. Resilience against missing credentials (API keys) for high-performance search.
6. Zero-config registry lookups (auto-resolving index URLs from internal metadata).
7. Graceful failure when a repository is missing from the registry.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, cwd=None, description=""):
    print(f"--- {description} ---")
    print(f"CMD: {' '.join(cmd)}")
    try:
        # Stream output to stdout
        result = subprocess.run(cmd, cwd=cwd, check=True, text=True)
        print("OK.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"FAILED. Exit code: {e.returncode}")
        return False

def main():
    repo_root = Path(os.getcwd())
    print(f"Repository Root: {repo_root}")
    
    # Ensure we are at root
    if not (repo_root / "tools/adk_knowledge_ext").exists():
        print("Error: Must run from repository root.")
        sys.exit(1)

    tests = [
        {
            "name": "Manual Configuration (uvx)",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/manual_uvx/Dockerfile",
            "tag": "adk-test-manual"
        },
        {
            "name": "Extension Installation (uvx)",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/extension_uvx/Dockerfile",
            "tag": "adk-test-extension"
        },
        {
            "name": "Resilience: Invalid Version",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/resilience_invalid_version/Dockerfile",
            "tag": "adk-test-res-version"
        },
        {
            "name": "Resilience: Missing Index",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/resilience_missing_index/Dockerfile",
            "tag": "adk-test-res-index"
        },
        {
            "name": "Resilience: Missing API Key",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/resilience_no_api_key/Dockerfile",
            "tag": "adk-test-res-key"
        },
        {
            "name": "Registry: Valid Lookup",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/registry_lookup/Dockerfile",
            "tag": "adk-test-registry-ok"
        },
        {
            "name": "Registry: Unknown Repo",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/registry_miss/Dockerfile",
            "tag": "adk-test-registry-miss"
        },
        {
            "name": "Managed Setup (CLI Integration)",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/managed_setup/Dockerfile",
            "tag": "adk-test-managed-setup"
        },
        {
            "name": "Managed Setup (JSON Integration)",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/managed_json_setup/Dockerfile",
            "tag": "adk-test-managed-json"
        },
        {
            "name": "Managed Setup (Claude Code Mock)",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/managed_claude/Dockerfile",
            "tag": "adk-test-managed-claude"
        }
    ]
    
    failed = []
    
    for test in tests:
        # Build
        print(f"\n=== Building {test['name']} ===")
        build_cmd = [
            "podman", "build",
            "-t", test["tag"],
            "-f", test["dockerfile"],
            "."
        ]
        if not run_command(build_cmd, cwd=repo_root, description=f"Build {test['tag']}"):
            failed.append(test["name"] + " (Build)")
            continue
            
        # Run Verification
        print(f"\n=== Verifying {test['name']} ===")
        run_cmd = [
            "podman", "run", "--rm",
            test["tag"]
        ]
        if not run_command(run_cmd, description=f"Run {test['tag']}"):
            failed.append(test["name"] + " (Verification)")
            
    if failed:
        print(f"\n\nTests FAILED: {failed}")
        sys.exit(1)
    else:
        print("\n\nAll Integration Tests PASSED.")

if __name__ == "__main__":
    main()
