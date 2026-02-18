#!/usr/bin/env python3
import os
import sys
import subprocess
import glob
import json

try:
    from dotenv import load_dotenv
    # Load root .env to ensure GEMINI_API_KEY is available for the subprocesses
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

    
# Clean vertex overrides so ADC works if needed
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_PROJECT"] = "ivanmkc-test"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

def test_all_agents():
    # Find all generated python files
    generated_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "generated_agents"))
    if not os.path.exists(generated_dir):
        print(f"Error: {generated_dir} does not exist. Have the agents finished generating?")
        sys.exit(1)
        
    py_files = glob.glob(os.path.join(generated_dir, "*.py"))
    if not py_files:
        print(f"No python files found in {generated_dir}")
        sys.exit(1)
        
    print(f"Found {len(py_files)} ADK agents for testing.\n")
    
    success_count = 0
    failure_count = 0
    failed_agents = []
    
    for py_file in py_files:
        basename = os.path.basename(py_file)
        print(f"=== Testing {basename} ===")
        
        try:
            # We run the script as a subprocess and stream its output to stdout
            # Ensure python subprocesses pick up our environment
            sub_env = os.environ.copy()
                
            # Use sys.executable instead of "python3" to ensure we stay inside our venv!
            result = subprocess.run(
                [sys.executable, py_file],
                cwd=generated_dir,
                env=sub_env,
                capture_output=True,
                text=True,
                timeout=45 # Increased timeout to 45s for more complex LLM agents
            )
            
            if result.returncode == 0:
                print(f"✅ Success: {basename}")
                success_count += 1
            else:
                print(f"❌ Failed: {basename}")
                print(f"--- Stdout ---\n{result.stdout}")
                print(f"--- Stderr ---\n{result.stderr}")
                failure_count += 1
                failed_agents.append(basename)
                
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout: {basename} hung for > 30 seconds.")
            failure_count += 1
            failed_agents.append(basename)
        except Exception as e:
            print(f"❌ Error executing {basename}: {e}")
            failure_count += 1
            failed_agents.append(basename)
            
        print("\n")
        
    print(f"=== Test Summary ===")
    print(f"Total Agents Tested: {len(py_files)}")
    print(f"Pass: {success_count}")
    print(f"Fail: {failure_count}")
    
    if failure_count > 0:
        print("Failed Agents:")
        for agent in failed_agents:
            print(f"  - {agent}")
        sys.exit(1)
    else:
        print("🎉 All generated agents passed execution successfully!")
        sys.exit(0)

if __name__ == "__main__":
    test_all_agents()
