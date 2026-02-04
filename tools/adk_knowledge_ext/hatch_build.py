import os
import sys
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

# Ensure src is in path to import build_utils
sys.path.append(str(Path(__file__).parent / "src"))
from adk_knowledge_ext.build_utils import bundle_indices

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root)
        src_dir = root / "src" / "adk_knowledge_ext"
        data_dir = src_dir / "data"
        
        # 1. Run Bundling Logic
        bundle_indices(src_dir, data_dir)

        # 2. Process Instructions Template (Generic Fallback)
        # We generate a generic INSTRUCTIONS.md that server.py might override or use as base
        target_version = os.environ.get("TARGET_VERSION", "main")
        target_repo_url = os.environ.get("TARGET_REPO_URL")
        
        template_path = root / "INSTRUCTIONS.template.md"
        output_path = data_dir / "INSTRUCTIONS.md"
        
        if template_path.exists():
            content = template_path.read_text()
            content = content.replace("{{TARGET_REPO_URL}}", target_repo_url or "(Determined at Runtime)")
            content = content.replace("{{TARGET_VERSION}}", target_version)
            output_path.write_text(content)
        else:
            print("Build Hook Warning: INSTRUCTIONS.template.md not found.")

        # 3. Embed Git SHA
        import subprocess
        try:
            git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            git_sha = "unknown"
        
        version_file = src_dir / "_version_git.py"
        version_file.write_text(f'GIT_SHA = "{git_sha}"\n')