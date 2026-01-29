
# Common Multi-Agent Patterns using ADK Primitives

By combining ADK's composition primitives, you can implement various established patterns for multi-agent collaboration.

### Coordinator/Dispatcher Pattern

* **Structure:** A central [`LlmAgent`](../agents/llm-agents.md) (Coordinator) manages several specialized `sub_agents`.
* **Goal:** Route incoming requests to the appropriate specialist agent.

### Sequential Pipeline Pattern

* **Structure:** A [`SequentialAgent`](../agents/workflow-agents.md) contains `sub_agents` executed in a fixed order.
* **Goal:** Implement a multi-step process where the output of one step feeds into the next.

### Parallel Fan-Out/Gather Pattern

* **Structure:** A [`ParallelAgent`](../agents/workflow-agents.md) runs multiple `sub_agents` concurrently, often followed by a later agent (in a `SequentialAgent`) that aggregates results.
* **Goal:** Execute independent tasks simultaneously to reduce latency, then combine their outputs.

### Hierarchical Task Decomposition

* **Structure:** A multi-level tree of agents where higher-level agents break down complex goals and delegate sub-tasks to lower-level agents.
* **Goal:** Solve complex problems by recursively breaking them down into simpler, executable steps.

### Review/Critique Pattern (Generator-Critic)

* **Structure:** Typically involves two agents within a [`SequentialAgent`](../agents/workflow-agents.md): a Generator and a Critic/Reviewer.
* **Goal:** Improve the quality or validity of generated output by having a dedicated agent review it.

### Iterative Refinement Pattern

* **Structure:** Uses a [`LoopAgent`](../agents/workflow-agents.md) containing one or more agents that work on a task over multiple iterations.
* **Goal:** Progressively improve a result (e.g., code, text, plan) stored in the session state until a quality threshold is met or a maximum number of iterations is reached.

### Human-in-the-Loop Pattern

* **Structure:** Integrates human intervention points within an agent workflow.
* **Goal:** Allow for human oversight, approval, correction, or tasks that AI cannot perform.
