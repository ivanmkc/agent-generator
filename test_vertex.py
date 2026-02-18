import os
from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel
from anthropic import AnthropicVertex

# --- CONFIGURATION ---
PROJECT_ID = "endless-fire-485722-a6"
CLAUDE_REGION = "us-east5"
PROJECT_REGION = "us-central1"

def test_gemini():
    print(f"\n--- Testing Gemini (Google) ---")
    try:
        vertexai.init(project=PROJECT_ID, location=PROJECT_REGION)
        model = GenerativeModel("gemini-2.5-flash") # Use a fast model for testing
        response = model.generate_content("Say 'Gemini is online!'")
        print(f"Result: {response.text.strip()}")
    except Exception as e:
        print(f"Gemini Error: {e}")

def test_claude():
    print(f"\n--- Testing Claude (Anthropic) ---")
    try:
        client = AnthropicVertex(project_id=PROJECT_ID, region=CLAUDE_REGION)
        # Note: Managed API model ID for Claude Sonnet
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Say 'Claude is online!'"}]
        )
        # Accessing content safely for Claude 3.5
        print(f"Result: {message.content[0].text}")
    except Exception as e:
        print(f"Claude Error: {e}")

if __name__ == "__main__":
    print(f"Starting Vertex AI Connectivity Test for project: {PROJECT_ID}")
    test_gemini()
    test_claude()
