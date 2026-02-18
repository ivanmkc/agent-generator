
# Troubleshooting

This section provides solutions to common issues you might encounter when working with the Agent Development Kit (ADK).

## GKE Deployment Issues

### 403 Permission Denied for `Gemini 2.0 Flash`

This usually means that the Kubernetes service account does not have the necessary permission to access the Vertex AI API. Ensure that you have created the service account and bound it to the `Vertex AI User` role as described in the [Configure Kubernetes Service Account for Vertex AI](../deployment/04_deploy_to_gke.md#configure-kubernetes-service-account-for-vertex-ai) section. If you are using AI Studio, ensure that you have set the `GOOGLE_API_KEY` environment variable in the deployment manifest and it is valid.

### Attempt to write a readonly database

You might see there is no session id created in the UI and the agent does not respond to any messages. This is usually caused by the SQLite database being read-only. This can happen if you run the agent locally and then create the container image which copies the SQLite database into the container. The database is then read-only in the container.

To fix this issue, you can either:

Delete the SQLite database file from your local machine before building the container image. This will create a new SQLite database when the container is started.

```bash
rm -f sessions.db
```

or (recommended) you can add a `.dockerignore` file to your project directory to exclude the SQLite database from being copied into the container image.

```
sessions.db
```

Build the container image abd deploy the application again.

## Model Access Issues

### API Key Not Found or Invalid

If you are using a model from a provider that requires an API key (e.g., Google AI Studio, OpenAI, Anthropic), make sure you have set the API key as an environment variable correctly. Also, double-check that the API key is valid and has the necessary permissions.

### Model Not Found

If you are using a model from a self-hosted endpoint (e.g., vLLM, Ollama), make sure the model is running and the endpoint is accessible from your agent. Also, check the model name and the API base URL in your agent's configuration.

## Tool Usage Issues

### Tool Not Found

If you are getting a "Tool not found" error, make sure you have added the tool to the agent's `tools` list. Also, check the tool's name and make sure it matches the name you are using in the agent's instructions.

### Incorrect Tool Arguments

If the tool is being called with incorrect arguments, check the tool's docstring and the agent's instructions. The docstring should clearly explain the tool's parameters, and the instructions should guide the agent on how to use the tool correctly.
