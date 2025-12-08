import asyncio
import os
import json
from pathlib import Path
from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator import GeminiCliCloudRunAnswerGenerator
from benchmarks.benchmark_candidates import get_gcloud_project

async def check_extension_installation():
    project_id = get_gcloud_project()
    if not project_id:
        print("Error: Could not determine Google Cloud Project ID.")
        return

    # Create generator instances for each service
    adk_python_generator = GeminiCliCloudRunAnswerGenerator(
        dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/adk-python"),
        service_name="adk-python",
        project_id=project_id,
        auto_deploy=False # We assume it's already deployed or will be deployed by other means
    )

    adk_docs_ext_generator = GeminiCliCloudRunAnswerGenerator(
        dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext"),
        service_name="adk-docs-ext",
        project_id=project_id,
        auto_deploy=False # We assume it's already deployed or will be deployed by other means
    )
    
    # Setup generators (resolves service URLs)
    print(f"Setting up {adk_python_generator.service_name}...")
    await adk_python_generator.setup()
    print(f"Setting up {adk_docs_ext_generator.service_name}...")
    await adk_docs_ext_generator.setup()

    generators_to_check = {
        "adk-python": adk_python_generator,
        "adk-docs-ext": adk_docs_ext_generator,
    }

    for service_name, generator in generators_to_check.items():
        if not generator.service_url:
            print(f"Skipping {service_name}: Service URL not found.")
            continue

        print(f"Checking extensions for {service_name}...")
        try:
            # Use a dummy prompt, as mcp list doesn't need one
            response_dict, _ = await generator._run_cli_command("mcp list --output-format json")
            
            stdout = response_dict.get("stdout", "")
            
            # The actual output might be wrapped in another dict if run through cli_server.py
            # Try to parse again if it looks like a string of JSON
            try:
                cli_output = json.loads(stdout)
            except json.JSONDecodeError:
                cli_output = {}

            servers = cli_output.get("servers", [])
            
            found_server = False
            for server in servers:
                if server.get("name") == service_name and server.get("status") == "Connected":
                    found_server = True
                    print(f"  ✅ {service_name} server is Connected.")
                    # Optionally, check for specific tools if the output includes them
                    if "tools" in server:
                        print(f"    Tools for {service_name}: {', '.join([t['name'] for t in server['tools']])}")
                    break
            
            if not found_server:
                print(f"  ❌ {service_name} server not found or not Connected.")
                print(f"  Full MCP list output: {stdout}")

        except Exception as e:
            print(f"Error checking {service_name}: {e}")

if __name__ == "__main__":
    # Set dummy API key if not set, to allow CLI to run for mcp list
    if not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = "dummy-api-key"
    
    asyncio.run(check_extension_installation())
