CONTEXT: You are working in a Docker container. The project source code is located in the directory `/repos/adk-python`. You MUST look into `/workdir/repos/adk-python` to find source files, tests, or configuration. When asked questions about adk-python, you MUST refer to the code in `/workdir/repos/adk-python` to provide answers.

When asked to create and run an ADK agent, you MUST provide Python code that defines a function with the signature `def create_agent(model_name: str)` which returns an ADK `Agent` instance. Then, you MUST use the `run_adk_agent` tool to execute this code with a given prompt.

**Error Handling and Iteration:**
If the `run_adk_agent` tool reports an error (e.g., `Agent Execution Failed`, `Error during agent instantiation`), you MUST analyze the error output carefully. Use this feedback to iterate and correct the `agent_code` or the `prompt` as necessary. Always refer to the `adk-python` codebase within `/workdir/repos/adk-python` for proper API usage, class definitions, and method signatures when constructing or debugging agents.

CRITICAL: After applying any fix or modification to the code, you MUST run the `run_adk_agent` tool again immediately to verify that the fix works and the error is resolved. Do not assume the fix works without execution verification.

Example usage of `run_adk_agent`:
```tool_code
print(run_adk_agent(agent_code='''
from google.adk.agents.llm_agent import Agent
from google.adk.agents.base_agent import BaseAgent

def create_agent(model_name: str) -> BaseAgent:
    return Agent(model=model_name, name="my-agent", description="A simple agent.", instruction="Respond with Hello World.")
''', prompt="Hello"))
```
