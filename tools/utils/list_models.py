
"""
Utility to list available models for the Google Gen AI SDK.

This script attempts to authenticate using the configured GEMINI_API key
and print the list of models available to the account. Useful for debugging
model name changes or deprecations.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from google.genai import Client
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType

def list_models():
    """
    Authenticates with the Gemini API and lists all available models.
    """
    api_key = API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)
    if not api_key:
        print("No API key available.")
        return

    client = Client(api_key=api_key)
    try:
        # Check if list_models is supported or how to list models in this SDK version
        # Based on documentation it might be client.models.list_models() or similar
        # Since I am not sure about the exact method signature for this specific google.genai version wrapper
        # I will try the standard way. 
        # Actually the error message said "Call ListModels"
        
        # In google-genai 0.3+, it's client.models.list()
        
        models = client.models.list()
        print("Available Models:")
        for m in models:
            print(f"- {m.name}")
            
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
