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

## 4. Fix Errors (Implementation from Spec)

**Description:**
Despite the name `fix_errors`, this suite is primarily an **Implementation Challenge**. The agent is provided with a "broken" or scaffolded Python file (which may contain syntax errors, missing imports, or empty function stubs) and a rigorous test file (the "Spec"). The agent's task is to write or correct the code to satisfy the requirements defined by the tests and the benchmark description.

**Motivation:**
Evaluates the agent's ability to **implement features from a technical specification** (the tests). It tests end-to-end coding capability: interpreting requirements, resolving dependencies, and producing syntactically and semantically valid code that passes a test harness.

**Example:**
> **Task:** `fix_errors:01_minimal_llm_agent`
> **Spec:** "Create a minimal LlmAgent named 'single_agent'."
> **Input State:** `unfixed.py` might contain `agent = LlmAgent(name="my agent")` (invalid name) or just `pass`.
> **Goal:** Generate a valid `create_agent` function that returns a correctly configured `LlmAgent` instance, passing the `test_agent.py` validation checks.

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
