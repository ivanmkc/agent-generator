
# Using Anthropic models

You can integrate Anthropic's Claude models directly using their API key or from a Vertex AI backend into your Java ADK applications by using the ADK's `Claude` wrapper class.

For Vertex AI backend, see the [Third-Party Models on Vertex AI](#third-party-models-on-vertex-ai-eg-anthropic-claude) section.

**Prerequisites:**

1.  **Dependencies:**
    *   **Anthropic SDK Classes (Transitive):** The Java ADK's `com.google.adk.models.Claude` wrapper relies on classes from Anthropic's official Java SDK. These are typically included as **transitive dependencies**.

2.  **Anthropic API Key:**
    *   Obtain an API key from Anthropic. Securely manage this key using a secret manager.

**Integration:**

Instantiate `com.google.adk.models.Claude`, providing the desired Claude model name and an `AnthropicOkHttpClient` configured with your API key. Then, pass this `Claude` instance to your `LlmAgent`.
