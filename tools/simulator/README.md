# Gemini CLI Python Simulator

This directory contains a standalone, headless Python simulation harness
designed to test the `gemini-cli` Node.js package. This ensures the CLI tool
registry, telemetry logging, and core decision logic work natively without being
obstructed by interactive TTY (Ink UI) racing conditions.

## Architecture

The simulator is built on a modular architecture to support extensibility and
separation of concerns:

- **`simulator.py`**: The entry point facade.
- **`harness.py`**: Abstract base class (`BaseSimulatorHarness`) and concrete
  implementations for different backends (`GeminiCliHarness`,
  `ClaudeCodeHarness`, etc.).
- **`runner.py`**: Orchestrates the simulation loop (`SimulationRunner`) and the
  user simulant (`LLMUserSimulant`).
- **`models.py`**: Pydantic data models defining the simulation state, cases,
  and results.

The harness utilizes the native `-p/--prompt` (Headless) and `-r/--resume` flags
to simulate multi-turn interactions with the user simulator LLM
(`LLMUserSimulant`).

### Supported Backends

- **gemini-cli**: The primary target. Uses experimental
  `GEMINI_APPROVAL_MODE=yolo`.
- **claude-code**: Evaluated side-by-side using Anthropic's node CLI.
- **antigravity**: Internal agentic framework backend.
- **codex**: Experimental backend.

> **Note**: The harness includes automatic retry logic for
> `429 RESOURCE_EXHAUSTED` errors from the Gemini API to verify agent behavior
> robustly even under rate limits.

## Running Tests (Recommended)

The ONLY supported method for running integration tests (especially with
`claude-code`) is via the hermetic podman runner. This ensures a consistent
environment and handles all dependency installation.

1. **Authentication:** Create a `.env` file in the `simulator/` directory with
   your API keys:

   ```env
   GEMINI_API_KEY="AIza..."
   ANTHROPIC_API_KEY="sk-ant-..."
   ```

2. **Execution:** Launch the wrapper shell script:
   ```bash
   ./podman_test.sh
   ```
   This script autonomously builds the Docker images, installs dependencies,
   runs `pytest`, and dumps artifacts to `outputs/<RUN_TIMESTAMP>`.

_(Note: The `claude-code` container supports `~/.claude.json` mapping if `.env`
auth is skipped)_

## Running Tests Locally (Legacy / Debug Only)

You can run tests natively with `pytest` for quick debugging of `gemini-cli`
only, but this is NOT guaranteed to work for all backends:

```bash
cd simulator
python3 -m pytest tests/integration/ --backend=gemini-cli
```

## Test Artifacts & Logs

After a run is completed, outputs are routed into heavily organized timestamp
folders mapping backend performance characteristics side-by-side.

All interaction trails are logged into:

- `outputs/<run_timestamp>/<backend>/<case>/session.log`
- `outputs/<run_timestamp>/<backend>/<case>/metadata.json`

At the climax of the test suite execution, the `podman_test.sh` orchestration
script will evaluate all metrics to compile and export:

- `outputs/<run_timestamp>/final_report.md`

## Agent Generation

The simulator includes a utility to mass-generate `adk-python` agents by
simulating an expert developer persona.

### Usage

```bash
python3 generate_agents.py
```

This script:

1. Iterates through a list of defined **Agent Personas** (e.g., "Universal Fact
   Checker", "Polyglot Translator").
2. Spins up a `gemini-cli` session with a prompt to write the agent code to
   `generated_agents/<agent_name>.py`.
3. **Verifies** the agent by instructing the CLI to execute the generated script
   locally and fix any errors.
4. Extracts the final, working python file to `../generated_agents/`.

This automated "coding loop" ensures that the generated agents are not just
hallucinated code, but valid, executable Python scripts that have passed a local
smoke test.
