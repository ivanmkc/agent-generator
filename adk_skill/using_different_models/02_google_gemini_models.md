
# Using Google Gemini Models

This is the most direct way to use Google's flagship models within ADK.

**Integration Method:** Pass the model's identifier string directly to the
`model` parameter of `LlmAgent` (or its alias, `Agent`).

**Backend Options & Setup:**

The `google-genai` library, used internally by ADK for Gemini, can connect
through either Google AI Studio or Vertex AI.

### Google AI Studio

* **Use Case:** Google AI Studio is the easiest way to get started with Gemini.
  All you need is the [API key](https://aistudio.google.com/app/apikey). Best
  for rapid prototyping and development.
* **Setup:** Typically requires an API key:
     * Set as an environment variable or 
     * Passed during the model initialization via the `Client` (see example below)

```shell
export GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

* **Models:** Find all available models on the
  [Google AI for Developers site](https://ai.google.dev/gemini-api/docs/models).

### Vertex AI

* **Use Case:** Recommended for production applications, leveraging Google Cloud
  infrastructure. Gemini on Vertex AI supports enterprise-grade features,
  security, and compliance controls.
* **Setup:**
    * Authenticate using Application Default Credentials (ADC):

        ```shell
        gcloud auth application-default login
        ```

    * Configure these variables either as environment variables or by providing them directly when initializing the Model.
            
         Set your Google Cloud project and location:
    
         ```shell
         export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
         export GOOGLE_CLOUD_LOCATION="YOUR_VERTEX_AI_LOCATION" # e.g., us-central1
         ```     
    
         Explicitly tell the library to use Vertex AI:
    
         ```shell
         export GOOGLE_GENAI_USE_VERTEXAI=TRUE
         ```

* **Models:** Find available model IDs in the
  [Vertex AI documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models).
