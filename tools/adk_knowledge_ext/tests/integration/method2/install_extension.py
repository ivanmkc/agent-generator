import json
import os
from pathlib import Path

def install():
    print("--- Simulating Extension Installation ---")
    
    ext_path = Path("/tmp/pkg/gemini-extension.json")
    if not ext_path.exists():
        print(f"Extension definition not found at {ext_path}")
        exit(1)
        
    with open(ext_path, "r") as f:
        ext_data = json.load(f)
        
    servers = ext_data.get("mcpServers", {})
    
    settings_dir = Path("/root/.gemini")
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"
    
    current_settings = {}
    if settings_path.exists():
        with open(settings_path, "r") as f:
            current_settings = json.load(f)
            
    if "mcpServers" not in current_settings:
        current_settings["mcpServers"] = {}
        
    # Merge
    print(f"Installing servers: {list(servers.keys())}")
    current_settings["mcpServers"].update(servers)
    
    with open(settings_path, "w") as f:
        json.dump(current_settings, f, indent=2)
        
    print(f"Settings updated at {settings_path}")

if __name__ == "__main__":
    install()
