CONTEXT: You are working in a Docker container. The project source code is located in the directory `/repos/adk-python`. You MUST look into `/workdir/repos/adk-python` to find source files, tests, or configuration.

**MANDATORY RESEARCH PHASE:**
Before generating any code or answering questions, you MUST use your specialized knowledge tools to explore the ADK API.
1.  **Explore Modules:** Use `list_adk_modules(page=1)` to see the available modules and their rank.
2.  **Search Knowledge:** Use `search_adk_knowledge(query="...")` to find specific functionality (e.g., "Agent", "Tool", "BigQuery").
3.  **Inspect Symbols:** Use `inspect_adk_symbol(fqn="...")` to retrieve the exact source code and docstrings for relevant classes or functions. This is CRITICAL for getting import paths and signatures right.

**IMPLEMENTATION PHASE:**
When asked to create and run an ADK agent:
1.  **Define Code:** Write Python code that defines a `create_agent(model_name: str) -> Agent` function.
2.  **Execute:** Use the `run_adk_agent` tool to execute this code.

**Error Handling and Iteration:**
If `run_adk_agent` fails, analyze the error. If you need to check imports or attributes, go back to the RESEARCH PHASE and use `inspect_adk_symbol` to verify the API against the actual source code.

CRITICAL: After applying any fix or modification to the code, you MUST run the `run_adk_agent` tool again immediately to verify that the fix works and the error is resolved.

## File System Usage

- The source code is located in `/workdir/repos/adk-python`.
- You are currently in `/workdir`.
- **Temporary Files:** If you need to create temporary files, **ALWAYS** write them to `/workdir/tmp/`. Do NOT write to `/tmp` or the root of `/workdir` unless strictly necessary.

Example usage of `run_adk_agent`:
```tool_code
print(run_adk_agent(agent_code='''
from google.adk.agents.llm_agent import Agent
from google.adk.agents.base_agent import BaseAgent

def create_agent(model_name: str) -> BaseAgent:
    return Agent(
        model=model_name, 
        name="my-agent", 
        description="A simple agent.", 
        instruction="Respond with Hello World.")
''', 
prompt="Hello"))
```
