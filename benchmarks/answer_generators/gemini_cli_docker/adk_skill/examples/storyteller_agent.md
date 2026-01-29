
# Storyteller Agent

This example demonstrates how to create a custom agent that generates a story based on a given topic. The `StoryFlowAgent` orchestrates a series of LLM agents to generate a story, critique it, revise it, and perform final checks.

## Goal

Create a system that generates a story, iteratively refines it through critique and revision, performs final checks, and regenerates the story if the final tone check fails.

## Why Custom?

The core requirement driving the need for a custom agent here is the **conditional regeneration based on the tone check**. Standard workflow agents don't have built-in conditional branching based on the outcome of a sub-agent's task. We need custom logic (`if tone == "negative": ...`) within the orchestrator.

## Implementation

### 1. Simplified custom agent Initialization

```python
from google.adk.agents import LlmAgent, BaseAgent, LoopAgent, SequentialAgent

class StoryFlowAgent(BaseAgent):
    """
    Custom agent for a story generation and refinement workflow.
    This agent orchestrates a sequence of LLM agents to generate a story,
    critique it, revise it, check grammar and tone, and potentially
    regenerate the story if the tone is negative.
    """
    story_generator: LlmAgent
    critic: LlmAgent
    reviser: LlmAgent
    grammar_check: LlmAgent
    tone_check: LlmAgent
    loop_agent: LoopAgent
    sequential_agent: SequentialAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        story_generator: LlmAgent,
        critic: LlmAgent,
        reviser: LlmAgent,
        grammar_check: LlmAgent,
        tone_check: LlmAgent,
    ):
        loop_agent = LoopAgent(
            name="CriticReviserLoop", sub_agents=[critic, reviser], max_iterations=2
        )
        sequential_agent = SequentialAgent(
            name="PostProcessing", sub_agents=[grammar_check, tone_check]
        )
        sub_agents_list = [
            story_generator,
            loop_agent,
            sequential_agent,
        ]
        super().__init__(
            name=name,
            story_generator=story_generator,
            critic=critic,
            reviser=reviser,
            grammar_check=grammar_check,
            tone_check=tone_check,
            loop_agent=loop_agent,
            sequential_agent=sequential_agent,
            sub_agents=sub_agents_list,
        )
```

### 2. Defining the Custom Execution Logic

```python
from typing import AsyncGenerator
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

@override
async def _run_async_impl(
    self, ctx: InvocationContext
) -> AsyncGenerator[Event, None]:
    """
    Implements the custom orchestration logic for the story workflow.
    """
    # 1. Initial Story Generation
    async for event in self.story_generator.run_async(ctx):
        yield event

    # 2. Critic-Reviser Loop
    async for event in self.loop_agent.run_async(ctx):
        yield event

    # 3. Sequential Post-Processing (Grammar and Tone Check)
    async for event in self.sequential_agent.run_async(ctx):
        yield event

    # 4. Tone-Based Conditional Logic
    tone_check_result = ctx.session.state.get("tone_check_result")
    if tone_check_result == "negative":
        async for event in self.story_generator.run_async(ctx):
            yield event
```

### 3. Defining the LLM Sub-Agents

```python
GEMINI_2_FLASH = "gemini-2.5-flash"

story_generator = LlmAgent(
    name="StoryGenerator",
    model=GEMINI_2_FLASH,
    instruction="""You are a story writer. Write a short story (around 100 words) about a cat,
based on the topic provided in session state with key 'topic'""",
    output_key="current_story",
)

critic = LlmAgent(
    name="Critic",
    model=GEMINI_2_FLASH,
    instruction="""You are a story critic. Review the story provided in
session state with key 'current_story'. Provide 1-2 sentences of constructive criticism
on how to improve it. Focus on plot or character.""",
    output_key="criticism",
)

reviser = LlmAgent(
    name="Reviser",
    model=GEMINI_2_FLASH,
    instruction="""You are a story reviser. Revise the story provided in
session state with key 'current_story', based on the criticism in
session state with key 'criticism'. Output only the revised story.""",
    output_key="current_story",
)

grammar_check = LlmAgent(
    name="GrammarCheck",
    model=GEMINI_2_FLASH,
    instruction="""You are a grammar checker. Check the grammar of the story
provided in session state with key 'current_story'. Output only the suggested
corrections as a list, or output 'Grammar is good!' if there are no errors.""",
    output_key="grammar_suggestions",
)

tone_check = LlmAgent(
    name="ToneCheck",
    model=GEMINI_2_FLASH,
    instruction="""You are a tone analyzer. Analyze the tone of the story
provided in session state with key 'current_story'. Output only one word: 'positive' if
the tone is generally positive, 'negative' if the tone is generally negative, or 'neutral'
otherwise.""",
    output_key="tone_check_result",
)
```
