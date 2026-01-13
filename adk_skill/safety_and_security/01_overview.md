
# Safety & Security for AI Agents

## Overview

As AI agents grow in capability, ensuring they operate safely, securely, and align with your brand values is paramount. Uncontrolled agents can pose risks, including executing misaligned or harmful actions, such as data exfiltration, and generating inappropriate content that can impact your brand’s reputation. **Sources of risk include vague instructions, model hallucination, jailbreaks and prompt injections from adversarial users, and indirect prompt injections via tool use.**

[Google Cloud's Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview) provides a multi-layered approach to mitigate these risks, enabling you to build powerful *and* trustworthy agents. It offers several mechanisms to establish strict boundaries, ensuring agents only perform actions you've explicitly allowed:

1. **Identity and Authorization**: Control who the agent **acts as** by defining agent and user auth.
2. **Guardrails to screen inputs and outputs:** Control your model and tool calls precisely.
3. **Sandboxed code execution:** Prevent model-generated code to cause security issues by sandboxing the environment
4. **Evaluation and tracing**: Use evaluation tools to assess the quality, relevance, and correctness of the agent's final output. Use tracing to gain visibility into agent actions to analyze the steps an agent takes to reach a solution, including its choice of tools, strategies, and the efficiency of its approach.
5. **Network Controls and VPC-SC:** Confine agent activity within secure perimeters (like VPC Service Controls) to prevent data exfiltration and limit the potential impact radius.
