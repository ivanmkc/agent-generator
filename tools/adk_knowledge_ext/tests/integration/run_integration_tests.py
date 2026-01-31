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
            "name": "Method 1: Manual Settings",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/method1/Dockerfile",
            "tag": "adk-test-method1"
        },
        {
            "name": "Method 2: Extension Installation",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/method2/Dockerfile",
            "tag": "adk-test-method2"
        },
        {
            "name": "Method 3: Resilience (Corrupt Data)",
            "dockerfile": "tools/adk_knowledge_ext/tests/integration/method3/Dockerfile",
            "tag": "adk-test-method3"
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