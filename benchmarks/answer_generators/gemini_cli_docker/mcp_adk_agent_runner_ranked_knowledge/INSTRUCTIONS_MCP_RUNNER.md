CONTEXT: You are working in a Docker container. The project source code is located in the directory `/repos/adk-python`. You MUST look into `/workdir/repos/adk-python` to find source files, tests, or configuration.

**MANDATORY RESEARCH PHASE:**
Before generating any code or answering questions, you MUST use your specialized knowledge tools to explore the ADK API.

1.  **BROWSE FIRST (Required):** Always start by calling `list_adk_modules(page=1)` to see the ranked list of available modules and classes. This reveals the most important entry points (like `Agent`, `Runner`, `Tool`) without guessing keywords.
    *   *Do not skip this step.* It prevents hallucination by grounding you in the actual API structure.
2.  **Inspect Symbols:** Once you identify a relevant class or function FQN from the list, use `inspect_adk_symbol(fqn="...")` to retrieve its exact source code and docstrings.
3.  **Last Resort Search:** Only use `search_adk_knowledge(query="keyword1 keyword2")` if you cannot find the functionality by browsing the module list. This tool supports multiple space-separated keywords for better filtering. Keyword search is brittle; rely on the ranked module list first.

**CRITICAL FALLBACK PROTOCOL:**
If `inspect_adk_symbol` returns "No file path recorded" or fails to provide the source code:
1.  **DO NOT HALLUCINATE.** Do not guess the API signature based on general conventions.
2.  **ACTIVATE FALLBACK:** Immediately use `run_shell_command` with `grep -r "class MyClass" .` or `find . -name "my_file.py"` to locate the file on disk.
3.  **READ MANUALLY:** Once located, use `read_file` (or `cat` via shell) to inspect the content directly.

**EVIDENCE CITATION REQUIREMENT:**
When reasoning about the code or answering a question, you must explicitly **QUOTE** the specific line of code, docstring, or method signature you retrieved that supports your answer.
- **BAD:** "I believe the class uses X because that's standard."
- **GOOD:** "The `LlmAgent` constructor signature in `llm_agent.py` shows: `def __init__(self, model: str, ...)`."

**IMPLEMENTATION PHASE:**
When asked to create and run an ADK agent:
1.  **Define Code:** Write Python code that defines a `create_agent(model_name: str) -> Agent` function.
2.  **Execute:** Use the `run_adk_agent` tool to execute this code.

**Error Handling and Iteration:**
If `run_adk_agent` fails, analyze the error. If you need to check imports or attributes, go back to the RESEARCH PHASE and use `inspect_adk_symbol` (or fallback tools) to verify the API against the actual source code.

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
