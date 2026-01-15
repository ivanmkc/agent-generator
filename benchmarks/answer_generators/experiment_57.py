import sys
import os
from pathlib import Path
import tempfile
import json
from typing import AsyncGenerator, Optional
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent
from google.adk.events import Event
from google.genai import types
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedTeardownAgent, RotatingKeyGemini
from benchmarks.answer_generators.experiment_55 import _create_logged_retrieval_agents
from benchmarks.data_models import ApiUnderstandingAnswerOutput, MultipleChoiceAnswerOutput, FixErrorAnswerOutput

class RawClientFormatterAgent(Agent):
    def __init__(self, model_client, **kwargs):
        super().__init__(**kwargs)
        self._model_client = model_client

    async def _run_async_impl(self, ctx):
        sanitized_request = ctx.session.state.get('sanitized_user_request', '')
        expert_answer = ctx.session.state.get('expert_answer', '')
        target_schema = FixErrorAnswerOutput
        schema_name = 'fix_error'
        if 'multiple choice' in sanitized_request.lower():
            target_schema = MultipleChoiceAnswerOutput
            schema_name = 'multiple_choice'
        elif 'class' in sanitized_request.lower():
            target_schema = ApiUnderstandingAnswerOutput
            schema_name = 'api_understanding'

        prompt = f'''You are a strict Output Formatter. Your job is to extract the answer from the Expert's response and format it according to the requested schema.

ORIGINAL REQUEST: {sanitized_request}

EXPERT ANSWER: {expert_answer}

INSTRUCTIONS:
- Extract the core answer.
- Extract the rationale/explanation.
- For API questions, ensure 'fully_qualified_class_name' is the full Python import path.
- For MCQs, extract just the letter (A, B, C, D) for the 'answer' field.
- Ensure the 'benchmark_type' field is set to '{schema_name}'.'''

        try:
            client = self._model_client.api_client
            response = await client.aio.models.generate_content(
                model=self._model_client.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=target_schema,
                    temperature=0.0
                )
            )
            if response.text:
                final_json = response.text
                # Try to inject benchmark_type if missing
                try:
                    data = json.loads(final_json)
                    if 'benchmark_type' not in data:
                        data['benchmark_type'] = schema_name
                        final_json = json.dumps(data)
                except:
                    pass
                ctx.session.state['final_expert_output'] = final_json
                yield Event(author=self.name, content=types.Content(role='model', parts=[types.Part(text=final_json)]))
            else:
                 ctx.session.state['final_expert_output'] = json.dumps({'benchmark_type': schema_name, 'code': '', 'rationale': 'Empty response', 'answer': 'A'})
        except Exception as e:
            ctx.session.state['final_expert_output'] = json.dumps({'benchmark_type': schema_name, 'code': '', 'rationale': str(e), 'answer': 'A'})

class FinalRelayAgent(Agent):
    async def _run_async_impl(self, ctx):
        final_json = ctx.session.state.get('final_expert_output', '')
        yield Event(author=self.name, content=types.Content(role='model', parts=[types.Part(text=final_json)]))

def create_knowledge_only_v37_generator(model_name, api_key_manager=None, adk_branch='v1.20.0'):
    name_prefix = 'ADK_KNOWLEDGE_V37'
    workspace_root = Path(tempfile.mkdtemp(prefix='adk_know_v37_'))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/'venv')
    model_pro = RotatingKeyGemini(model='gemini-2.5-pro', api_key_manager=api_key_manager) if api_key_manager else 'gemini-2.5-pro'
    model_flash = RotatingKeyGemini(model='gemini-2.5-flash', api_key_manager=api_key_manager) if api_key_manager else 'gemini-2.5-flash'
    setup_agent = SetupAgentCodeBased(name='setup_agent', workspace_root=workspace_root, tools_helper=tools_helper)
    prompt_sanitizer = PromptSanitizerAgent(model=model_flash, include_contents='none', output_key='sanitized_user_request')
    retrieval_agents = _create_logged_retrieval_agents(tools_helper, model_flash)
    knowledge_expert = LlmAgent(name='knowledge_expert', model=model_pro, include_contents='none', output_key='expert_answer', instruction='Answer naturally.')
    formatter = RawClientFormatterAgent(name='formatter', model_client=model_flash)
    finalizer = FinalRelayAgent(name='finalizer')
    agent = SequentialAgent(name='adk_v37', sub_agents=[setup_agent, prompt_sanitizer, *retrieval_agents, knowledge_expert, formatter, finalizer])
    return AdkAnswerGenerator(agent=agent, name=f'{name_prefix}(Decoupled)', setup_hook=setup_hook, api_key_manager=api_key_manager, model_name='mixed')
