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
> **Code Snippet:**
> ```python
> def snippet_agent_creation_issue_1(**kwargs):
>     # LlmAgent instantiation missing 'model' argument
>     root_agent = LlmAgent(
>         name="my_agent", instruction="You are a helpful assistant.", **kwargs
>     )
> ```
> **Question:** What is the primary reason this `LlmAgent` instantiation fails?
> **Answer:** The `LlmAgent` class is missing the required `model` argument.

## 4. Fix Errors (Implementation from Spec)

**Description:**
Despite the name `fix_errors`, this suite is primarily an **Implementation Challenge**. The agent is provided with a "broken" or scaffolded Python file (which may contain syntax errors, missing imports, or empty function stubs) and a rigorous test file (the "Spec"). The agent's task is to write or correct the code to satisfy the requirements defined by the tests and the benchmark description.

**Motivation:**
Evaluates the agent's ability to **implement features from a technical specification** (the tests). It tests end-to-end coding capability: interpreting requirements, resolving dependencies, and producing syntactically and semantically valid code that passes a test harness.

**Example:**
> **Task:** `fix_errors:01_minimal_llm_agent`
> **Input State (`unfixed.py`):**
> ```python
> def create_agent(model_name: str) -> BaseAgent:
>   # Spec: Create a helpful LlmAgent named "single_agent"
>   raise NotImplementedError("Agent implementation incomplete.")
> ```
> **Expected Output (`fixed.py`):**
> ```python
> def create_agent(model_name: str) -> BaseAgent:
>   root_agent = LlmAgent(
>       name="single_agent",
>       model=model_name,
>       instruction="You are a helpful assistant.",
>   )
>   return root_agent
> ```

## 5. Predict Runtime Behavior (`predict_runtime_behavior_mc`)
