import json
import os
from pathlib import Path

def install():
    print("--- Simulating Extension Installation ---")
    
    ext_path = Path("/tmp/pkg/codebase-extension.json")
    if not ext_path.exists():
        print(f"Extension definition not found at {ext_path}")
        exit(1)
        
    with open(ext_path, "r") as f:
        ext_data = json.load(f)
        
    servers = ext_data.get("mcpServers", {})
    
    # Customize for test:
    # 1. Point 'uvx --from' to local /tmp/pkg instead of git repo
    # 2. Add real repo URL and local index URL
    for k in servers:
        # Patch args: Replace git URL with local path
        args = servers[k].get("args", [])
        for i, arg in enumerate(args):
            if arg.startswith("git+"):
                args[i] = "/tmp/pkg"
        
        servers[k]["env"]["TARGET_REPO_URL"] = "https://github.com/google/adk-python.git"
        servers[k]["env"]["TARGET_VERSION"] = "v1.20.0"
        servers[k]["env"]["TARGET_INDEX_URL"] = "file:///tmp/local_index.yaml"

    settings_dir = Path("/root/.gemini")
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"
    
    current_settings = {"mcpServers": servers}
    
    with open(settings_path, "w") as f:
        json.dump(current_settings, f, indent=2)
        
    print(f"Settings updated at {settings_path}")

if __name__ == "__main__":
    install()
