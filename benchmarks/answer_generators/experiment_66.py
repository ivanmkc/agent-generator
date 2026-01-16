"""
Experiment 66: Statistical Discovery V46 (Ranked Index Retrieval).

Builds on V45 (Task-Aware Solver) but switches the index source to 'ranked_targets.yaml'.
This new index provides a flattened, ranked list of seeds (classes/methods) with usage scores.

Key Changes:
- Seed Selector uses `ranked_targets.yaml`.
- Docstring Fetcher pulls details directly from `ranked_targets.yaml` (offline).
- Context Expander is disabled.
- Single Step Solver used for answer generation.
- Decoupled Formatting.
- **NEW:** Sanitizer disabled for testing.
"""

from pathlib import Path
import tempfile
import json
import re
import yaml
import datetime
from typing import AsyncGenerator, Optional, List

from pydantic import PrivateAttr

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager, KeyType
from benchmarks.data_models import (
    GeneratedAnswer,
    BenchmarkGenerationError,
    FixErrorBenchmarkCase,
    ApiUnderstandingBenchmarkCase,
    MultipleChoiceBenchmarkCase,
    FixErrorAnswerOutput,
    ApiUnderstandingAnswerOutput,
    MultipleChoiceAnswerOutput,
    BaseBenchmarkCase,
    TraceLogEvent,
    TraceEventType
)
from benchmarks.answer_generators.adk_context import adk_execution_context

from google.adk.agents import LlmAgent, SequentialAgent, Agent, InvocationContext
from google.adk.events import Event
from google.genai import types
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedTeardownAgent, RotatingKeyGemini
from google.adk.tools import FunctionTool, ToolContext

"""
Experiment 66: Statistical Discovery V46 (Ranked Index Retrieval).

Builds on V45 (Task-Aware Solver) but switches the index source to 'ranked_targets.yaml'.
This new index provides a flattened, ranked list of seeds (classes/methods) with usage scores.

Key Changes:
- Seed Selector uses `ranked_targets.yaml`.
- Docstring Fetcher pulls details directly from `ranked_targets.yaml` (offline).
- Context Expander is disabled.
- Single Step Solver used for answer generation.
- Decoupled Formatting.
- **NEW:** Sanitizer disabled for testing.
"""

from pathlib import Path
import tempfile
import json
import re
import yaml
import datetime
from typing import AsyncGenerator, Optional, List

from pydantic import PrivateAttr

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager, KeyType
from benchmarks.data_models import (
    GeneratedAnswer,
    BenchmarkGenerationError,
    FixErrorBenchmarkCase,
    ApiUnderstandingBenchmarkCase,
    MultipleChoiceBenchmarkCase,
    FixErrorAnswerOutput,
    ApiUnderstandingAnswerOutput,
    MultipleChoiceAnswerOutput,
    BaseBenchmarkCase,
    TraceLogEvent,
    TraceEventType
)
from benchmarks.answer_generators.adk_context import adk_execution_context

from google.adk.agents import LlmAgent, SequentialAgent, Agent, InvocationContext
from google.adk.events import Event
from google.genai import types
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedTeardownAgent, RotatingKeyGemini
from google.adk.tools import FunctionTool, ToolContext

# --- Agents ---

class SingleStepSolver(LlmAgent):
    """Answers the question in a single turn using the retrieved context."""
    def __init__(self, model, **kwargs):
        super().__init__(
            name="single_step_solver",
            model=model,
            tools=[],  # No tools, relies on history/context
            include_contents='default',
            output_key="final_response", # Capture output for TeardownAgent
            instruction=(
                "You are the ADK Expert Solver.\n"
                "Review the conversation history above, which contains the retrieval steps, inspection results, and docstrings.\n"
                "**REQUEST:**\n"
                "{user_request}\n\n"
                "**GOAL:**\n"
                "Answer the request using ONLY the provided context and the specific instructions in the Request.\n"
                "1. **Coding Tasks:** Implement EXACTLY what is asked. Do not hallucinate factory patterns or boilerplate unless requested. Use the retrieved API signatures.\n"
                "2. **API Questions:** Identify the Fully Qualified Name (FQN) and provide the exact import path. **Prefer the defining base class** (e.g., `BaseAgent` for `find_agent`, `App` for `plugins`) unless the question specifies a subclass.\n"
                "3. **Parameter Names:** Use the EXACT field name found in the inspection output (e.g., `output_key`, not `output_to_session`).\n"
                "4. **Multiple Choice:** Evaluate the options against the retrieved docstrings.\n\n"
                "**OUTPUT:**\n"
                "Provide a detailed, natural language response containing the code, FQNs, or reasoning required."
            ),
            **kwargs
        )

def _create_hierarchical_retrieval_agent(tools_helper: AdkTools, model) -> Agent:
    
    def save_selected_seeds(seeds: list[str], tool_context: ToolContext) -> str:
        """Saves the selected seeds and marks retrieval as complete."""
        tool_context.session.state["relevant_modules_json"] = json.dumps({"modules": seeds})
        return f"Seeds saved: {seeds}. Retrieval complete."

    async def list_ranked_targets(page: int = 1, tool_context: ToolContext = None) -> str:
        """Lists ranked ADK targets from the index, paginated at 100 items per page."""
        return tools_helper.list_ranked_targets(page=page)

    async def inspect_fqn(fqn: str, tool_context: ToolContext) -> str:
        """Inspects a Python object (class or module) to reveal docstrings, hierarchy, and members."""
        return await tools_helper.inspect_fqn(fqn)

    async def search_ranked_targets(query: str | list[str], page: int = 1, tool_context: ToolContext = None) -> str:
        """Searches the ranked index of ADK symbols by keyword(s). Supports pagination."""
        return tools_helper.search_ranked_targets(query, page=page)

    hierarchical_agent = LlmAgent(
        name="hierarchical_retrieval_agent",
        model=model,
        tools=[
             FunctionTool(list_ranked_targets),
             FunctionTool(search_ranked_targets),
             FunctionTool(inspect_fqn),
             FunctionTool(save_selected_seeds)
        ],
        include_contents="default",
        instruction=(
             "You are the Hierarchical Retrieval Agent. Your goal is to find the relevant ADK classes/methods for the user request.\n\n"
             "**TOOLS:**\n"
             "1. `search_ranked_targets(query, page)`: Search the index by keyword (or list of keywords). FASTEST way to find symbols. Use next pages if needed.\n"
             "2. `list_ranked_targets(page)`: Browse the ranked index. Useful if keyword search fails.\n"
             "3. `inspect_fqn(fqn)`: Inspect a specific symbol. GETS FULL DETAILS (docstrings, hierarchy, members).\n"
             "4. `save_selected_seeds(seeds)`: Call this when you have found the necessary information to answer the user request.\n\n"
             "**STRATEGY:**\n"
             "- **Search First:** Use `search_ranked_targets` with a list of keywords from the request (e.g., `['logging', 'session', 'max_iterations']`).\n"
             "- **Parameters? Check Configs:** If asked about a parameter (e.g., 'static instruction'), check the **CONFIG** class (e.g., `LlmAgentConfig`, `BaseAgentConfig`) in addition to the Agent class.\n"
             "- **Search Broadly:** If 'observer' returns nothing, try synonyms like 'log', 'monitor', 'telemetry'. If 'sequence' fails, try 'sequential'.\n"
             "- **Inspect Everything:** Never guess a parameter name. Inspect the class to see the exact field name (e.g., `output_key` vs `output_to_session`).\n"
             "- **Inheritance:** If a method is found on a subclass but defined in a Base class (check MRO), note the Base class FQN.\n"
             "- **Finalize:** Once you verify the exact symbol/parameter exists, call `save_selected_seeds` and stop."
             "\n\nRequest: {user_request}"
        )
    )
    
    return hierarchical_agent

# --- Generator with Post-Processing ---

class PostProcessedAdkAnswerGenerator(AdkAnswerGenerator):
    """
    Runs the ADK agent to get a text answer, then uses a separate Gemini call
    to format that text into the required JSON schema.
    """
    def __init__(self, model_client: RotatingKeyGemini, workspace_root: Path, **kwargs):
        super().__init__(**kwargs)
        self.model_client = model_client
        self.workspace_root = workspace_root

    async def generate_answer(self, benchmark_case: BaseBenchmarkCase, run_id: str) -> GeneratedAnswer:
        # 1. Determine Schema & Type
        if isinstance(benchmark_case, FixErrorBenchmarkCase):
            prompt = self._create_prompt_for_fix_error(benchmark_case)
            output_schema = FixErrorAnswerOutput
            b_type = "fix_error"
        elif isinstance(benchmark_case, ApiUnderstandingBenchmarkCase):
            prompt = self._create_prompt_for_api_understanding(benchmark_case)
            output_schema = ApiUnderstandingAnswerOutput
            b_type = "api_understanding"
        elif isinstance(benchmark_case, MultipleChoiceBenchmarkCase):
            prompt = self._create_prompt_for_multiple_choice(benchmark_case)
            output_schema = MultipleChoiceAnswerOutput
            b_type = "multiple_choice"
        else:
            raise TypeError(f"Unsupported benchmark case: {type(benchmark_case)}")

        api_key_id: Optional[str] = None
        token = None
        current_key = None

        if self.api_key_manager:
             current_key, api_key_id = self.api_key_manager.get_key_for_run(run_id, KeyType.GEMINI_API)
        
        token = adk_execution_context.set({"api_key": current_key, "key_id": api_key_id})
        
        try:
            # 2. Run ADK Agent (Produces Text)
            # We don't care about session files or JSON here, just the final text response.
            raw_text, trace_logs, usage_metadata, _ = await self._run_agent_async(prompt, api_key_id, b_type)
            
            # 3. Post-Process with Gemini (Text -> JSON)
            formatter_prompt = (
                f"You are a strict data formatter. Convert the following text into the required JSON schema.\n"
                f"Text:\n{raw_text}\n\n"
                f"Schema Requirement: Extract the answer for a '{b_type}' task.\n"
                f"- For 'fix_error', extract the full code block.\n"
                f"- For 'api_understanding', extract the FQN and code snippet.\n"
                f"- For 'multiple_choice', extract the answer letter.\n"
            )
            
            client = self.model_client.api_client 
            model_id = self.model_client.model 
            
            # Log the Formatter Prompt
            trace_logs.append(TraceLogEvent(
                type=TraceEventType.ADK_EVENT,
                source="orchestrator",
                timestamp=datetime.datetime.now().isoformat(),
                role="system",
                author="supervisor_formatter",
                content=formatter_prompt,
                details={"step": "Post-Process Formatter Input", "model": model_id}
            ))

            # Use structured output feature of Gemini 2.0
            response = await client.aio.models.generate_content(
                model=model_id,
                contents=formatter_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=output_schema
                )
            )
            
            # Log the Formatter Result
            trace_logs.append(TraceLogEvent(
                type=TraceEventType.MESSAGE,
                source="orchestrator",
                timestamp=datetime.datetime.now().isoformat(),
                role="model",
                author="supervisor_formatter",
                content=response.text or "EMPTY RESPONSE",
                details={"step": "Post-Process Formatter Output"}
            ))

            # 4. Parse & Validate
            if not response.text:
                raise ValueError("Formatter model returned empty response.")
                
            output = output_schema.model_validate_json(response.text)
            
            self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=True)
            return GeneratedAnswer(
                output=output, 
                trace_logs=trace_logs, 
                usage_metadata=usage_metadata,
                api_key_id=api_key_id
            )

        except Exception as e:
            if self.api_key_manager:
                self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=False, error_message=str(e))
            raise BenchmarkGenerationError(f"Generation failed: {e}", original_exception=e, api_key_id=api_key_id) from e
        finally:
            if token: adk_execution_context.reset(token)
            if self.api_key_manager:
                self.api_key_manager.release_run(run_id)


# --- Factory ---

def create_ranked_index_generator_v46(
    model_name: str, 
    api_key_manager: ApiKeyManager = None, 
    adk_branch='v1.20.0'
) -> AdkAnswerGenerator:
    
    name_prefix = 'ADK_RANKED_V46_POSTPROC'
    workspace_root = Path(tempfile.mkdtemp(prefix='adk_v46_'))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/'venv')
    
    # We need the client object for the post-processor
    gemini_client = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)

    # Agents
    setup_agent = SetupAgentCodeBased(name='setup_agent', workspace_root=workspace_root, tools_helper=tools_helper)
    
    hierarchical_agent = _create_hierarchical_retrieval_agent(tools_helper, gemini_client)
    solver = SingleStepSolver(model=gemini_client)
    teardown = CodeBasedTeardownAgent(name='teardown', workspace_root=workspace_root, tools_helper=tools_helper)

    # NO Formatter Agent in the chain!
    agent = SequentialAgent(
        name='adk_v46',
        sub_agents=[
            setup_agent, 
            hierarchical_agent,
            solver,
            teardown
        ]
    )

    return PostProcessedAdkAnswerGenerator(
        model_client=gemini_client,
        workspace_root=workspace_root,
        agent=agent, 
        name=f'{name_prefix}', 
        setup_hook=setup_hook, 
        api_key_manager=api_key_manager, 
        model_name=model_name
    )
