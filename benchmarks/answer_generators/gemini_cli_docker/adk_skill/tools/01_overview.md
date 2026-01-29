
# Tools

## What is a Tool?

In the context of ADK, a Tool represents a specific
capability provided to an AI agent, enabling it to perform actions and interact
with the world beyond its core text generation and reasoning abilities. What
distinguishes capable agents from basic language models is often their effective
use of tools.

Technically, a tool is typically a modular code component—**like a Python/ Java
function**, a class method, or even another specialized agent—designed to
execute a distinct, predefined task. These tasks often involve interacting with
external systems or data.

### Key Characteristics

**Action-Oriented:** Tools perform specific actions, such as:

* Querying databases
* Making API requests (e.g., fetching weather data, booking systems)
* Searching the web
* Executing code snippets
* Retrieving information from documents (RAG)
* Interacting with other software or services

**Extends Agent capabilities:** They empower agents to access real-time information, affect external systems, and overcome the knowledge limitations inherent in their training data.

**Execute predefined logic:** Crucially, tools execute specific, developer-defined logic. They do not possess their own independent reasoning capabilities like the agent's core Large Language Model (LLM). The LLM reasons about which tool to use, when, and with what inputs, but the tool itself just executes its designated function.

## How Agents Use Tools

Agents leverage tools dynamically through mechanisms often involving function calling. The process generally follows these steps:

1. **Reasoning:** The agent's LLM analyzes its system instruction, conversation history, and user request.
2. **Selection:** Based on the analysis, the LLM decides on which tool, if any, to execute, based on the tools available to the agent and the docstrings that describes each tool.
3. **Invocation:** The LLM generates the required arguments (inputs) for the selected tool and triggers its execution.
4. **Observation:** The agent receives the output (result) returned by the tool.
5. **Finalization:** The agent incorporates the tool's output into its ongoing reasoning process to formulate the next response, decide the subsequent step, or determine if the goal has been achieved.

Think of the tools as a specialized toolkit that the agent's intelligent core (the LLM) can access and utilize as needed to accomplish complex tasks.

## Tool Types in ADK

ADK offers flexibility by supporting several types of tools:

1. **[Function Tools](../tools/function-tools.md):** Tools created by you, tailored to your specific application's needs.
2. **[Built-in Tools](../tools/built-in-tools.md):** Ready-to-use tools provided by the framework for common tasks.
3. **[Third-Party Tools](../tools/third-party-tools.md):** Integrate tools seamlessly from popular external libraries.
