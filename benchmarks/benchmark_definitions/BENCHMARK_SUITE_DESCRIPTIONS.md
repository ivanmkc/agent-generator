# Benchmark Suite Descriptions

This document provides a detailed overview of the benchmark suites used to evaluate ADK Agents. Each suite targets a specific dimension of agent capability, from static knowledge recall to dynamic debugging.

## 1. API Understanding (`api_understanding`)

**Description:**
Evaluates the agent's knowledge of the ADK's public API surface. Questions focus on identifying the correct class names, method signatures, inheritance hierarchies, and mandatory parameters.

**Motivation:**
To ensure the agent is grounded in the actual library code and does not hallucinate non-existent classes or methods. A strong score here indicates the agent has a solid "mental map" of the ADK.

**Example:**
> **Question:** What is the foundational class for all agents in the ADK?
> **Answer:** `BaseAgent` (fully qualified: `google.adk.agents.base_agent.BaseAgent`)

## 2. Configure ADK Features (`configure_adk_features_mc`)

**Description:**
A multiple-choice suite testing the ability to correctly configure ADK components. Topics include setting up `RunConfig` (streaming, timeouts), configuring `LlmAgent` parameters (tools, system instructions), and managing `Session` state.

**Motivation:**
ADK features are often controlled by complex configuration objects. This suite verifies that the agent understands *how* to enable capabilities like context caching, resumption, or structured output.

**Example:**
> **Question:** Which parameter limits the number of iterations for a `LoopAgent`?
> - A: max_iterations
> - B: loop_limit
> - C: timeout
> - D: None of the above
> **Answer:** A (`max_iterations`)

## 3. Diagnose Setup Errors (`diagnose_setup_errors_mc`)

**Description:**
Presents code snippets containing subtle setup or configuration errors (e.g., invalid names, mutually exclusive arguments, type mismatches) and asks the agent to identify the specific error that would be raised at runtime.

**Motivation:**
Real-world usage often involves debugging broken configuration. This suite tests the agent's ability to act as a linter/debugger, spotting issues before execution.

**Example:**
> **Question:** You define an agent with an invalid name 'my-agent'. What validation error is raised?
> **Code Snippet:** `agent = LlmAgent(name="my-agent", ...)`
> **Answer:** `ValueError: Agent name must be a valid identifier.`

## 4. Fix Errors (`fix_errors`)

**Description:**
The most rigorous "coding" suite. The agent is given a broken Python file (e.g., missing imports, syntax errors, incorrect API usage) and a corresponding test file. The agent must generate a corrected version of the code that passes the tests.

**Motivation:**
Evaluates the agent's end-to-end coding capability: reading code, understanding error messages (implied or explicit), and synthesizing a valid solution that adheres to the framework's constraints.

**Example:**
> **Task:** Fix `01_single_llm_agent/unfixed.py`.
> **Issue:** The agent name contains spaces (`"my agent"`), causing a `ValueError`.
> **Goal:** Generate a valid `create_agent` function where the name is corrected (e.g., `"my_agent"`).

## 5. Predict Runtime Behavior (`predict_runtime_behavior_mc`)

**Description:**
Similar to "Diagnose Setup Errors", but focuses on *behavioral* predictions rather than just initialization crashes. Questions involve execution order (callbacks), state mutations, and tool interactions.

**Motivation:**
Tests the agent's deep understanding of the ADK's execution model (e.g., knowing that `before_tool_callback` runs *before* the tool, or how `SequentialAgent` passes state).

**Example:**
> **Question:** Is `session.state` mutable?
> **Answer:** Yes, it is a mutable dictionary-like object.

## 6. Search Relevance (`search_relevance`)

**Description:**
Evaluates the semantic retrieval capabilities of the agent (or the underlying RAG system). Questions are phrased in natural language describing a *goal* or *concept*, and the agent must identify the specific class or component that fulfills that need.

**Motivation:**
Users often know *what* they want to do ("retry failed steps") but not the class name (`ReflectAndRetryToolPlugin`). This suite measures the "Semantic Recall" of the knowledge system.

**Example:**
> **Question:** What class should I use if I want my agent to automatically reflect on its mistakes and retry failed turns?
> **Answer:** `ReflectAndRetryToolPlugin`
