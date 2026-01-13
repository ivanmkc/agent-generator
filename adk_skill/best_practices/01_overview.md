
# Best Practices for Building Agents with ADK

This section provides best practices and recommendations for building robust, effective, and maintainable agents using the Agent Development Kit (ADK).

## Agent Design

*   **Modularity and Specialization:** Instead of building a single monolithic agent, compose your application from multiple, smaller, specialized agents. This makes your system more modular, easier to test, and more maintainable.
*   **Clear Descriptions:** When creating agents, especially in a multi-agent system, provide clear and concise descriptions of their capabilities. This is crucial for the root agent to delegate tasks effectively.
*   **Model Selection:** Choose the right LLM for the job. Use more powerful and expensive models for complex reasoning and planning tasks, and smaller, faster models for simpler tasks like generating greetings or farewells.

## Tool Design

*   **Clear and Descriptive Docstrings:** The LLM relies heavily on the tool's docstring to understand its purpose, parameters, and return values. Write clear, concise, and accurate docstrings for all your tools.
*   **Simple and Focused Tools:** Design your tools to perform a single, well-defined task. This makes them easier for the LLM to understand and use.
*   **JSON-Serializable Types:** Use standard JSON-serializable types for your tool's parameters and return values.
*   **Descriptive Return Values:** The return values of your tools should be descriptive and easy for the LLM to understand. Instead of returning a boolean or a number, return a dictionary with a clear status and a descriptive message.

## Prompt Engineering

*   **Clear and Specific Instructions:** Provide clear and specific instructions to your agents. The more detailed the instructions, the better the LLM will be able to understand its role and how to use its tools.
*   **Few-Shot Examples:** For complex tasks or specific output formats, include a few-shot examples in the agent's instructions.
*   **Guide Tool Use:** Don't just list the tools available to the agent. Explain when and why the agent should use them.

## State Management

*   **Use State for Conversational Memory:** Use session state to store information that needs to be remembered across multiple turns in a conversation.
*   **Use the Right Scope:** Use the appropriate state prefix (`user:`, `app:`, `temp:`, or no prefix) to define the scope and persistence of your state variables.
*   **Avoid Storing Complex Objects in State:** Do not store complex, non-serializable objects in the session state. Instead, store simple identifiers and retrieve the complex objects from another source.

## Safety and Security

*   **Implement Guardrails:** Use callbacks like `before_model_callback` and `before_tool_callback` to implement safety guardrails that can inspect and block requests or tool calls based on predefined rules.
*   **Validate Inputs and Outputs:** Validate all inputs to your agents and tools to prevent prompt injection and other security vulnerabilities.
*   **Use Sandboxed Code Execution:** When using code execution tools, make sure to use a sandboxed environment to prevent the execution of malicious code.

## Evaluation

*   **Evaluate Both Trajectory and Final Response:** When evaluating your agents, it's important to evaluate both the final response and the trajectory the agent took to get there.
*   **Use a Combination of Automated and Human Evaluation:** Use automated evaluation for metrics that can be easily measured, and human evaluation for more subjective metrics like the quality of the agent's responses.
*   **Create a Comprehensive Evaluation Set:** Create a comprehensive evaluation set that covers a wide range of scenarios, including edge cases and potential failure modes.
