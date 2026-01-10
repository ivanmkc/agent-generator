# VibeShare

VibeShare is an evaluation and analysis suite for Large Language Models (LLMs), specifically designed to benchmark their knowledge of AI agent frameworks. It focuses on detecting mentions of modern orchestration libraries, with a particular emphasis on Google's **Agent Development Kit (ADK)**.

## Features

- **Multi-Model Support:** Integration with Gemini, Claude, GPT, Llama, and Grok via LiteLLM.
- **Framework Detection:** Automatically identifies mentions of 30+ AI frameworks (LangChain, CrewAI, AutoGen, etc.) in model responses.
- **ADK Focus:** Specialized detection logic for Google's Agent Development Kit (ADK) across multiple languages (Python, JS, Java, Go).
- **Two-Phase Pipeline:**
    - **Inference Phase:** Executes prompts with configurable concurrency and robust caching.
    - **Analysis Phase:** Processes cached responses into structured JSON reports with detected framework metadata.
- **Smart API Key Management:** Automated rotation and health reporting for API keys.
- **Caching:** Persistent storage of model responses to minimize costs.
- **Data Visualization:** Jupyter notebooks for comparing model performance and framework mindshare.

## Project Structure

- `analyze_vibeshare.py`: Main entry point for the analysis pipeline.
- `core.py`: Core logic for inference tasks and result generation.
- `config.py`: Configuration for models and concurrency limits.
- `models/`: Abstractions for different LLM interfaces.
- `data_models.py`: Pydantic models for structured data validation.
- `cache.py`: Management of the local result cache.
- `utils.py`: Utility functions for loading prompts and data.
- `visualization.ipynb`: Notebook for data analysis and visualization.

## Setup

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure API Keys:**
    VibeShare expects API keys to be managed via the `benchmarks.api_key_manager` (ensure this dependency is correctly configured in your environment).

3.  **Define Prompts:**
    Add your evaluation prompts to `prompts.yaml`.

## Usage

Run the full analysis pipeline:

```bash
python -m vibeshare.analyze_vibeshare
```

This will:
1. Verify model availability.
2. Run inference for all prompts across all configured models (using cache where available).
3. Generate `vibeshare_results.json` with the processed results.

## Testing

Run unit tests using `pytest`:

```bash
python -m pytest tests/unit
```

## Contributing

Please ensure that any new data models are added to `data_models.py` and new model integrations follow the pattern in `models/`.
