import json
import os
import sys

# Constants
EXTENSION_DIR = "/root/.gemini/extensions/adk-docs-ext"
CONFIG_PATH = os.path.join(EXTENSION_DIR, "gemini-extension.json")
MCPDOC_BIN = "/root/.local/bin/mcpdoc"

def make_absolute(path_str):
    """
    Converts a relative path to an absolute path rooted in EXTENSION_DIR.
    Leaves URLs and existing absolute paths untouched.
    """
    # Check for URLs
    if path_str.startswith("http://") or path_str.startswith("https://") or path_str.startswith("file://"):
        return path_str
    
    # Check for absolute paths
    if path_str.startswith("/"):
        return path_str
    
    # Prepend extension directory
    return os.path.join(EXTENSION_DIR, path_str)

def patch_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: Config file not found at {CONFIG_PATH}")
        sys.exit(1)

    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON config: {e}")
        sys.exit(1)

    # Locate the MCP server configuration
    # We target 'adk-docs-mcp' specifically as defined in the extension
    server = config.get("mcpServers", {}).get("adk-docs-mcp")
    if not server:
        print("Error: 'adk-docs-mcp' server configuration not found in gemini-extension.json.")
        sys.exit(1)

    print(f"Patching configuration for server: adk-docs-mcp")

    # 1. Update the executable command
    # Replace 'uvx' (or whatever was there) with the pre-installed binary
    print(f"Updating command: {server.get('command')} -> {MCPDOC_BIN}")
    server["command"] = MCPDOC_BIN

    # 2. Process arguments
    args = server.get("args", [])
    original_args_count = len(args)

    # Remove 'uvx' preamble if present
    # Heuristic: If it starts with '--from', it's likely 'uvx --from pkg cmd ...' (3 args)
    if len(args) >= 3 and args[0] == "--from":
        print("Detected 'uvx' preamble. Removing first 3 arguments.")
        args = args[3:]

    # 3. Fix relative paths in '--urls'
    if "--urls" in args:
        try:
            idx = args.index("--urls")
            # Iterate through arguments following '--urls'
            i = idx + 1
            while i < len(args):
                val = args[i]
                
                # Stop if we hit the next flag (starts with '-')
                # Note: This assumes paths don't start with '-'
                if val.startswith("-"):
                    break
                
                # Handle "name:path" format if present (though simple paths are standard here)
                # We simply check if the value looks like a path we should touch
                new_val = make_absolute(val)
                
                if new_val != val:
                    print(f"Resolving path: '{val}' -> '{new_val}'")
                    args[i] = new_val
                
                i += 1
        except ValueError:
            pass # Should not happen given 'if' check

    server["args"] = args
    
    # Write back the changes
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("Configuration patched successfully.")

if __name__ == "__main__":
    patch_config()
