
# Using Open & Local Models via LiteLLM

For maximum control, cost savings, privacy, or offline use cases, you can run
open-source models locally or self-host them and integrate them using LiteLLM.

**Integration Method:** Instantiate the `LiteLlm` wrapper class, configured to
point to your local model server.

### Ollama Integration

[Ollama](https://ollama.com/) allows you to easily run open-source models
locally.

#### Model choice

If your agent is relying on tools, please make sure that you select a model with
tool support from [Ollama website](https://ollama.com/search?c=tools).

For reliable results, we recommend using a decent-sized model with tool support.

### Self-Hosted Endpoint (e.g., vLLM)

Tools such as [vLLM](https://github.com/vllm-project/vllm) allow you to host
models efficiently and often expose an OpenAI-compatible API endpoint.
