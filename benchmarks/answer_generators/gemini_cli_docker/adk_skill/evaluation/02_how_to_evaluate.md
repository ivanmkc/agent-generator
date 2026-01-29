
# How to run Evaluation with the ADK

As a developer, you can evaluate your agents using the ADK in the following ways:

1. **Web-based UI (`adk web`):** Evaluate agents interactively through a web-based interface.
2. **Programmatically (`pytest`):** Integrate evaluation into your testing pipeline using `pytest` and test files.
3. **Command Line Interface (`adk eval`):** Run evaluations on an existing evaluation set file directly from the command line.

### 1. `adk web` - Run Evaluations via the Web UI

The web UI provides an interactive way to evaluate agents, generate evaluation datasets, and inspect agent behavior in detail.

### 2.  `pytest` - Run Tests Programmatically

You can also use **`pytest`** to run test files as part of your integration tests.

### 3. `adk eval` - Run Evaluations via the CLI

You can also run evaluation of an eval set file through the command line interface (CLI). This runs the same evaluation that runs on the UI, but it helps with automation, i.e. you can add this command as a part of your regular build generation and verification process.
