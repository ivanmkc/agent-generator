
# Using Cloud & Proprietary Models via LiteLLM

To access a vast range of LLMs from providers like OpenAI, Anthropic (non-Vertex
AI), Cohere, and many others, ADK offers integration through the LiteLLM
library.

**Integration Method:** Instantiate the `LiteLlm` wrapper class and pass it to
the `model` parameter of `LlmAgent`.

**LiteLLM Overview:** [LiteLLM](https://docs.litellm.ai/) acts as a translation
layer, providing a standardized, OpenAI-compatible interface to over 100+ LLMs.

**Setup:**

1. **Install LiteLLM:**
        ```shell
        pip install litellm
        ```
2. **Set Provider API Keys:** Configure API keys as environment variables for
   the specific providers you intend to use.

    * *Example for OpenAI:*

        ```shell
        export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
        ```

    * *Example for Anthropic (non-Vertex AI):*

        ```shell
        export ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"
        ```

    * *Consult the
      [LiteLLM Providers Documentation](https://docs.litellm.ai/docs/providers)
      for the correct environment variable names for other providers.*
