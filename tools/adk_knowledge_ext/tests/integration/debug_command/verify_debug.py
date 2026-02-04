import subprocess
import sys

def main():
    print("--- Verifying Debug Command ---")
    
    cmd = ["codebase-knowledge-mcp-manage", "debug"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    output = result.stdout + result.stderr
    print(output)
    
    if result.returncode != 0:
        print("FAIL: Debug command returned non-zero exit code.")
        sys.exit(1)
        
    checks = [
        "Git SHA:",
        "Server Self-Test",
        "Server Connection: OK",
        "list_modules",
        "File System & Paths",
        "Environment Variables",
        "Integration Status"
    ]
    
    failed = False
    for check in checks:
        if check not in output:
            print(f"FAIL: Missing expected output: '{check}'")
            failed = True
            
    if failed:
        sys.exit(1)
        
    print("SUCCESS: Debug command verified.")

if __name__ == "__main__":
    main()
