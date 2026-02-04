import pytest
import shutil
import os
from pathlib import Path
from benchmarks.answer_generators.gemini_cli_docker import GeminiCliPodmanAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import ImageDefinition, IMAGE_DEFINITIONS
from core.api_key_manager import ApiKeyManager
from core.models import ModelName

# Reuse the existing remote_main path as template
# We define it relative to the project root for clarity in copying, 
# but for ImageDefinition relative paths, we need relative to gemini_cli_docker dir.
REMOTE_MAIN_REL_PATH = "benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_remote_main"

@pytest.mark.asyncio
async def test_cloning_with_kb_ids(tmp_path):
    """
    Verifies that running setup --kb-ids pre-clones the repository into the image.
    """
    image_name = "gemini-cli:test_cloning_with_ids"
    
    # Use relative paths compatible with podman_utils logic
    # source_dir is relative to benchmarks/answer_generators/gemini_cli_docker/
    # We want project root (../../..)
    # dockerfile is relative to benchmarks/answer_generators/gemini_cli_docker/
    
    definitions = IMAGE_DEFINITIONS.copy()
    definitions[image_name] = ImageDefinition(
        source_dir="../../../",
        dockerfile="mcp_adk_agent_runner_remote_main/Dockerfile",
        description="Test image with kb_ids pre-configured",
        dependencies=["gemini-cli:base"],
        build_args={"BASE_IMAGE": "gemini-cli:base"}
    )
    
    generator = GeminiCliPodmanAnswerGenerator(
        image_definitions=definitions,
        image_name=image_name,
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=ApiKeyManager(),
    )
    
    await generator.setup()
    
    try:
        import subprocess
        
        print("Checking for pre-cloned repositories in container...")
        # Check if any directory exists in .mcp_cache (excluding logs/indices if any, but repos are top level dirs there)
        # We look for .git inside any subdir of .mcp_cache
        check_cmd = f"podman exec {generator.container_name} find /root/.mcp_cache -name .git -type d"
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        
        print(f"Result stdout: {result.stdout}")
        
        assert result.returncode == 0
        assert result.stdout.strip(), "No repositories found in .mcp_cache. Pre-cloning failed."
        
    finally:
        await generator.teardown()


@pytest.mark.asyncio
async def test_cloning_without_kb_ids(tmp_path):
    """
    Verifies that running setup WITHOUT --kb-ids (empty) does NOT pre-clone,
    but dynamic cloning works on demand.
    """
    # 1. Create a temp dockerfile dir
    variant_dir = tmp_path / "variant_no_ids"
    # Copy from project root
    shutil.copytree(Path.cwd() / REMOTE_MAIN_REL_PATH, variant_dir)
    
    # 2. Modify Dockerfile to remove --kb-ids "..."
    dockerfile_path = variant_dir / "Dockerfile"
    content = dockerfile_path.read_text()
    
    # Replace the setup command to be empty/quiet, AND ensure we use local code
    # Old: --kb-ids "adk-python-v1.20.0" \
    # New: --local "/app/extensions/adk-knowledge-ext" \ (and keep quiet/force if present, or add it)
    # The original line ends with \ and next line is --quiet.
    
    # We replace the whole kb-ids line with the local flag
    import re
    content = re.sub(r'--kb-ids "[^"]+" \\', r'--local "/app/extensions/adk-knowledge-ext" \\', content)
    dockerfile_path.write_text(content)
    
    image_name = "gemini-cli:test_cloning_no_ids"
    
    definitions = IMAGE_DEFINITIONS.copy()
    
    # For temp dir, we MUST use absolute paths.
    # We explicitly resolve them.
    abs_source = str(Path.cwd().resolve()) # We still need project root as context for COPY tools/...
    abs_dockerfile = str(dockerfile_path.resolve())
    
    definitions[image_name] = ImageDefinition(
        source_dir=abs_source,
        dockerfile=abs_dockerfile,
        description="Test image without kb_ids",
        dependencies=["gemini-cli:base"],
        build_args={"BASE_IMAGE": "gemini-cli:base"}
    )
    
    generator = GeminiCliPodmanAnswerGenerator(
        image_definitions=definitions,
        image_name=image_name,
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=ApiKeyManager(),
    )
    
    await generator.setup()
    
    try:
        import subprocess
        
        # 1. Check - Repo should NOT exist
        print("Checking for ABSENCE of pre-cloned repositories...")
        check_cmd = f"podman exec {generator.container_name} find /root/.mcp_cache -name .git -type d"
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        
        # find might fail if dir doesn't exist, or return empty
        # If .mcp_cache/repos doesn't exist, it's fine
        if result.returncode == 0:
             assert not result.stdout.strip(), f"Repositories found unexpectedly: {result.stdout}"
        
        # 2. Run Agent to trigger dynamic clone
        
        prompt = (
            "Please read the source code for `google.adk.agents.base_agent.BaseAgent` "
            "using `read_source_code` tool. kb_id='adk-python-v1.20.0'."
        )
        
        # We need an API Key for the agent run
        from core.api_key_manager import KeyType
        run_id = "test_dynamic_clone"
        api_key, _ = await generator.api_key_manager.get_key_for_run(run_id, KeyType.GEMINI_API)
        
        # Run CLI command
        # We use the generator's helper
        cmd_parts = [generator.cli_path, "--output-format", "json", "--yolo", "--model", generator.model_name, prompt]
        env = {"GEMINI_API_KEY": api_key}
        
        response, logs = await generator.run_cli_command(cmd_parts, extra_env=env)
        
        # 3. Check - Repo SHOULD exist now
        print("Checking for PRESENCE of dynamic repository...")
        result_after = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        assert result_after.returncode == 0
        assert result_after.stdout.strip(), "Repository not found after agent execution. Dynamic clone failed."
        assert result_after.returncode == 0
        assert result_after.stdout.strip(), "Repository not found after agent execution. Dynamic clone failed."
        
    finally:
        await generator.teardown()