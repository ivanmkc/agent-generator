# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""An AnswerGenerator that uses an ADK Agent to generate answers."""

import uuid

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from benchmarks.answer_generators.llm_base import LlmAnswerGenerator
from benchmarks.data_models import ApiUnderstandingAnswerOutput
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.data_models import FixErrorAnswerOutput
from benchmarks.data_models import FixErrorBenchmarkCase
from benchmarks.data_models import GeneratedAnswer
from benchmarks.data_models import MultipleChoiceAnswerOutput
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.data_models import TraceLogEvent
from benchmarks.data_models import UsageMetadata


class AdkAnswerGenerator(LlmAnswerGenerator):
  """An AnswerGenerator that uses an ADK Agent."""

  def __init__(self, agent: Agent, name: str | None = None):
    # Context handling is not primarily used for ADK agents yet, passing None
    super().__init__(context=None)
    self.agent = agent
    self._name = name or f"AdkAnswerGenerator({self.agent.name})"
    self.runner = InMemoryRunner(agent=self.agent)

  @property
  def name(self) -> str:
    """Returns a unique name for this generator instance."""
    return self._name

  async def generate_answer(
      self, benchmark_case: BaseBenchmarkCase
  ) -> GeneratedAnswer:
    """Generates an answer using the ADK Agent."""

    if isinstance(benchmark_case, FixErrorBenchmarkCase):
      prompt = self._create_prompt_for_fix_error(benchmark_case)
      output_schema_class = FixErrorAnswerOutput
    elif isinstance(benchmark_case, ApiUnderstandingBenchmarkCase):
      prompt = self._create_prompt_for_api_understanding(benchmark_case)
      output_schema_class = ApiUnderstandingAnswerOutput
    elif isinstance(benchmark_case, MultipleChoiceBenchmarkCase):
      prompt = self._create_prompt_for_multiple_choice(benchmark_case)
      output_schema_class = MultipleChoiceAnswerOutput
    else:
      raise TypeError(
          f"Unsupported benchmark case type: {type(benchmark_case)}"
      )

    # Run the agent asynchronously.
    response_text, trace_logs, usage_metadata = await self._run_agent_async(
        prompt
    )

    # Extract JSON from markdown code block if present
    if "```json" in response_text:
      json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
    else:
      json_str = response_text.strip()

    # Parse the JSON response into the appropriate Pydantic model.
    # This will raise a ValidationError if the schema doesn't match.
    output = output_schema_class.model_validate_json(json_str)
    return GeneratedAnswer(
        output=output, trace_logs=trace_logs, usage_metadata=usage_metadata
    )

  async def _run_agent_async(
      self, prompt: str
  ) -> tuple[str, list[TraceLogEvent], UsageMetadata]:
    """Helper to run the agent and get the response."""
    session_id = f"benchmark_session_{uuid.uuid4()}"
    session = await self.runner.session_service.create_session(
        app_name=self.runner.app_name,
        user_id="benchmark_user",
        session_id=session_id,
    )
    final_response = ""
    logs: list[TraceLogEvent] = []

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0

    new_message = types.UserContent(parts=[types.Part(text=prompt)])

    async for event in self.runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=new_message
    ):
      # Extract usage metadata if available
      if hasattr(event, "usage_metadata") and event.usage_metadata:
        # Note: ADK usage_metadata attributes might vary, assuming standard keys
        # We try to get attributes safely
        pmt = getattr(event.usage_metadata, "prompt_token_count", 0) or 0
        cpt = getattr(event.usage_metadata, "candidates_token_count", 0) or 0
        tt = getattr(event.usage_metadata, "total_token_count", 0) or 0

        total_prompt_tokens += pmt
        total_completion_tokens += cpt
        total_tokens += tt

      # Map ADK event to TraceLogEvent
      log_event = TraceLogEvent(
          type=getattr(event, "action", "ADK_EVENT"),
          source="adk",
          timestamp=(
              event.created_time.isoformat()
              if hasattr(event, "created_time") and event.created_time
              else None
          ),
          details=event.model_dump(),
      )

      # Try to determine role and content
      if hasattr(event, "action"):
        if event.action == "user_message":
          log_event.role = "user"
          log_event.type = "message"
        elif event.action == "model_response":
          log_event.role = "model"
          log_event.type = "message"
        elif event.action == "tool_use":
          log_event.type = "tool_use"
          log_event.role = "model"
          # Extract tool info if available in content or tool_use part
          # This depends on ADK internal structure for tool calls
          pass

      if event.content:
        # Convert ADK content to dict/str
        try:
          log_event.content = event.content.model_dump()
        except:
          log_event.content = str(event.content)

      logs.append(log_event)

      if event.is_final_response():
        if event.content and event.content.parts:
          final_response = event.content.parts[0].text
        # Don't break immediately if we want full traces?
        # Usually final response is the end, but let's keep breaking to match logic.
        break

    usage_metadata = UsageMetadata(
        total_tokens=total_tokens,
        prompt_tokens=total_prompt_tokens,
        completion_tokens=total_completion_tokens,
    )

    return final_response, logs, usage_metadata
