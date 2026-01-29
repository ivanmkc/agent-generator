
# Function tools

## What are function tools?

When out-of-the-box tools don't fully meet specific requirements, developers can create custom function tools. This allows for **tailored functionality**, such as connecting to proprietary databases or implementing unique algorithms.

ADK offers several ways to create functions tools, each suited to different levels of complexity and control:

1. Function Tool
2. Long Running Function Tool
3. Agents-as-a-Tool

## 1. Function Tool

Transforming a function into a tool is a straightforward way to integrate custom logic into your agents. In fact, when you assign a function to an agent’s tools list, the framework will automatically wrap it as a Function Tool for you. This approach offers flexibility and quick integration.

### Parameters

Define your function parameters using standard **JSON-serializable types** (e.g., string, integer, list, dictionary). It's important to avoid setting default values for parameters, as the language model (LLM) does not currently support interpreting them.

### Return Type

The preferred return type for a Function Tool is a **dictionary** in Python or **Map** in Java. This allows you to structure the response with key-value pairs, providing context and clarity to the LLM. If your function returns a type other than a dictionary, the framework automatically wraps it into a dictionary with a single key named **"result"**.

## 2. Long Running Function Tool

Designed for tasks that require a significant amount of processing time without blocking the agent's execution. This tool is a subclass of `FunctionTool`.

When using a `LongRunningFunctionTool`, your function can initiate the long-running operation and optionally return an **initial result** (e.g. the long-running operation id). Once a long running function tool is invoked the agent runner will pause the agent run and let the agent client to decide whether to continue or wait until the long-running operation finishes. The agent client can query the progress of the long-running operation and send back an intermediate or final response. The agent can then continue with other tasks. An example is the human-in-the-loop scenario where the agent needs human approval before proceeding with a task.

## 3. Agent-as-a-Tool

This powerful feature allows you to leverage the capabilities of other agents within your system by calling them as tools. The Agent-as-a-Tool enables you to invoke another agent to perform a specific task, effectively **delegating responsibility**. This is conceptually similar to creating a Python function that calls another agent and uses the agent's response as the function's return value.
