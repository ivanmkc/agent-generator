# ADK Python Library Index

This index maps module paths to their descriptions.

## `google.adk.agents`
No description available.
**Exports:** Agent, BaseAgent, LlmAgent, LoopAgent, ParallelAgent, SequentialAgent, InvocationContext, LiveRequest, LiveRequestQueue, RunConfig, McpInstructionProvider

## `google.adk.agents.active_streaming_tool`
No description available.
**Exports:** ActiveStreamingTool

## `google.adk.agents.agent_config`
No description available.
**Exports:** AgentConfig, agent_config_discriminator

## `google.adk.agents.base_agent`
No description available.
**Exports:** BaseAgent, BaseAgentState

## `google.adk.agents.base_agent_config`
No description available.
**Exports:** BaseAgentConfig

## `google.adk.agents.callback_context`
No description available.
**Exports:** CallbackContext

## `google.adk.agents.common_configs`
Common configuration classes for agent YAML configs.
**Exports:** AgentRefConfig, ArgumentConfig, CodeConfig

## `google.adk.agents.config_agent_utils`
No description available.
**Exports:** from_config, resolve_agent_reference, resolve_callbacks, resolve_code_reference, resolve_fully_qualified_name

## `google.adk.agents.context_cache_config`
No description available.
**Exports:** ContextCacheConfig

## `google.adk.agents.invocation_context`
No description available.
**Exports:** InvocationContext, LlmCallsLimitExceededError, RealtimeCacheEntry, new_invocation_context_id

## `google.adk.agents.live_request_queue`
No description available.
**Exports:** LiveRequest, LiveRequestQueue

## `google.adk.agents.llm_agent`
No description available.
**Exports:** Agent, LlmAgent

## `google.adk.agents.llm_agent_config`
No description available.
**Exports:** LlmAgentConfig

## `google.adk.agents.loop_agent`
Loop agent implementation.
**Exports:** LoopAgent, LoopAgentState

## `google.adk.agents.loop_agent_config`
Loop agent implementation.
**Exports:** LoopAgentConfig

## `google.adk.agents.mcp_instruction_provider`
Provides instructions to an agent by fetching prompts from an MCP server.
**Exports:** McpInstructionProvider

## `google.adk.agents.parallel_agent`
Parallel agent implementation.
**Exports:** ParallelAgent

## `google.adk.agents.parallel_agent_config`
Parallel agent implementation.
**Exports:** ParallelAgentConfig

## `google.adk.agents.readonly_context`
No description available.
**Exports:** ReadonlyContext

## `google.adk.agents.run_config`
No description available.
**Exports:** RunConfig, StreamingMode

## `google.adk.agents.sequential_agent`
Sequential agent implementation.
**Exports:** SequentialAgent, SequentialAgentState

## `google.adk.agents.sequential_agent_config`
Config definition for SequentialAgent.
**Exports:** SequentialAgentConfig

## `google.adk.agents.transcription_entry`
No description available.
**Exports:** TranscriptionEntry

## `google.adk.apps`
No description available.
**Exports:** App, ResumabilityConfig

## `google.adk.apps.app`
No description available.
**Exports:** App, EventsCompactionConfig, ResumabilityConfig, validate_app_name

## `google.adk.apps.base_events_summarizer`
No description available.
**Exports:** BaseEventsSummarizer

## `google.adk.apps.llm_event_summarizer`
No description available.
**Exports:** LlmEventSummarizer

## `google.adk.artifacts`
No description available.
**Exports:** BaseArtifactService, FileArtifactService, GcsArtifactService, InMemoryArtifactService

## `google.adk.artifacts.artifact_util`
Utility functions for handling artifact URIs.
**Exports:** ParsedArtifactUri, get_artifact_uri, is_artifact_ref, parse_artifact_uri

## `google.adk.artifacts.base_artifact_service`
No description available.
**Exports:** ArtifactVersion, BaseArtifactService

## `google.adk.artifacts.file_artifact_service`
No description available.
**Exports:** FileArtifactService, FileArtifactVersion

## `google.adk.artifacts.gcs_artifact_service`
An artifact service implementation using Google Cloud Storage (GCS).
**Exports:** GcsArtifactService

## `google.adk.artifacts.in_memory_artifact_service`
No description available.
**Exports:** InMemoryArtifactService

## `google.adk.auth.auth_credential`
No description available.
**Exports:** AuthCredential, AuthCredentialTypes, BaseModelWithConfig, HttpAuth, HttpCredentials, OAuth2Auth, ServiceAccount, ServiceAccountCredential

## `google.adk.auth.auth_handler`
No description available.
**Exports:** AuthHandler

## `google.adk.auth.auth_schemes`
No description available.
**Exports:** ExtendedOAuth2, OAuthGrantType, OpenIdConnectWithConfig

## `google.adk.auth.auth_tool`
No description available.
**Exports:** AuthConfig, AuthToolArguments

## `google.adk.auth.credential_manager`
No description available.
**Exports:** CredentialManager

## `google.adk.auth.credential_service.base_credential_service`
No description available.
**Exports:** BaseCredentialService

## `google.adk.auth.credential_service.in_memory_credential_service`
No description available.
**Exports:** InMemoryCredentialService

## `google.adk.auth.credential_service.session_state_credential_service`
No description available.
**Exports:** SessionStateCredentialService

## `google.adk.auth.exchanger`
Credential exchanger module.
**Exports:** BaseCredentialExchanger

## `google.adk.auth.exchanger.base_credential_exchanger`
Base credential exchanger interface.
**Exports:** BaseCredentialExchanger, CredentialExchangeError

## `google.adk.auth.exchanger.credential_exchanger_registry`
Credential exchanger registry.
**Exports:** CredentialExchangerRegistry

## `google.adk.auth.exchanger.oauth2_credential_exchanger`
OAuth2 credential exchanger implementation.
**Exports:** OAuth2CredentialExchanger

## `google.adk.auth.oauth2_credential_util`
No description available.
**Exports:** create_oauth2_session, update_credential_with_tokens

## `google.adk.auth.oauth2_discovery`
No description available.
**Exports:** AuthorizationServerMetadata, OAuth2DiscoveryManager, ProtectedResourceMetadata

## `google.adk.auth.refresher`
Credential refresher module.
**Exports:** BaseCredentialRefresher

## `google.adk.auth.refresher.base_credential_refresher`
Base credential refresher interface.
**Exports:** BaseCredentialRefresher, CredentialRefresherError

## `google.adk.auth.refresher.credential_refresher_registry`
Credential refresher registry.
**Exports:** CredentialRefresherRegistry

## `google.adk.auth.refresher.oauth2_credential_refresher`
OAuth2 credential refresher implementation.
**Exports:** OAuth2CredentialRefresher

## `google.adk.cli.adk_web_server`
No description available.
**Exports:** AddSessionToEvalSetRequest, AdkWebServer, ApiServerSpanExporter, AppInfo, CreateEvalSetRequest, CreateSessionRequest, EvalResult, GetEventGraphResult, InMemoryExporter, ListAppsResponse, ListEvalResultsResponse, ListEvalSetsResponse, ListMetricsInfoResponse, RunAgentRequest, RunEvalRequest, RunEvalResponse, RunEvalResult, SaveArtifactRequest, UpdateMemoryRequest, UpdateSessionRequest

## `google.adk.cli.agent_graph`
No description available.
**Exports:** build_graph, get_agent_graph

## `google.adk.cli.built_in_agents`
Agent Builder Assistant for ADK.
**Exports:** AgentBuilderAssistant, agent

## `google.adk.cli.built_in_agents.adk_agent_builder_assistant`
Agent factory for creating Agent Builder Assistant with embedded schema.
**Exports:** AgentBuilderAssistant

## `google.adk.cli.built_in_agents.sub_agents`
Sub-agents for Agent Builder Assistant.
**Exports:** create_google_search_agent, create_url_context_agent

## `google.adk.cli.built_in_agents.sub_agents.google_search_agent`
Sub-agent for Google Search functionality.
**Exports:** create_google_search_agent

## `google.adk.cli.built_in_agents.sub_agents.url_context_agent`
Sub-agent for URL context fetching functionality.
**Exports:** create_url_context_agent

## `google.adk.cli.built_in_agents.tools`
Tools for Agent Builder Assistant.
**Exports:** read_config_files, write_config_files, cleanup_unused_files, delete_files, read_files, write_files, search_adk_source, explore_project

## `google.adk.cli.built_in_agents.tools.cleanup_unused_files`
Cleanup unused files tool for Agent Builder Assistant.
**Exports:** cleanup_unused_files

## `google.adk.cli.built_in_agents.tools.delete_files`
File deletion tool for Agent Builder Assistant.
**Exports:** delete_files

## `google.adk.cli.built_in_agents.tools.explore_project`
Project explorer tool for analyzing structure and suggesting file paths.
**Exports:** explore_project

## `google.adk.cli.built_in_agents.tools.query_schema`
ADK AgentConfig schema query tool for dynamic schema information access.
**Exports:** query_schema

## `google.adk.cli.built_in_agents.tools.read_config_files`
Configuration file reader tool for existing YAML configs.
**Exports:** read_config_files

## `google.adk.cli.built_in_agents.tools.read_files`
File reading tool for Agent Builder Assistant.
**Exports:** read_files

## `google.adk.cli.built_in_agents.tools.search_adk_knowledge`
ADK knowledge search tool.
**Exports:** error_response, post_request, search_adk_knowledge

## `google.adk.cli.built_in_agents.tools.search_adk_source`
ADK source code search tool for Agent Builder Assistant.
**Exports:** search_adk_source

## `google.adk.cli.built_in_agents.tools.write_config_files`
Configuration file writer tool with validation-before-write.
**Exports:** write_config_files

## `google.adk.cli.built_in_agents.tools.write_files`
File writing tool for Agent Builder Assistant.
**Exports:** write_files

## `google.adk.cli.built_in_agents.utils`
Utility modules for Agent Builder Assistant.
**Exports:** load_agent_config_schema, find_adk_source_folder, get_adk_schema_path

## `google.adk.cli.built_in_agents.utils.adk_source_utils`
Utilities for finding ADK source folder dynamically and loading schema.
**Exports:** clear_schema_cache, find_adk_source_folder, get_adk_schema_path, load_agent_config_schema

## `google.adk.cli.built_in_agents.utils.path_normalizer`
Helpers for normalizing file path strings produced by the model.
**Exports:** sanitize_generated_file_path

## `google.adk.cli.built_in_agents.utils.resolve_root_directory`
Working directory helper tool to resolve path context issues.
**Exports:** resolve_file_path, resolve_file_paths

## `google.adk.cli.cli`
No description available.
**Exports:** InputFile, run_cli, run_input_file, run_interactively

## `google.adk.cli.cli_create`
No description available.
**Exports:** run_cmd

## `google.adk.cli.cli_deploy`
No description available.
**Exports:** to_agent_engine, to_cloud_run, to_gke

## `google.adk.cli.cli_eval`
No description available.
**Exports:** get_eval_sets_manager, get_root_agent, parse_and_get_evals_to_run, pretty_print_eval_result, try_get_reset_func

## `google.adk.cli.cli_tools_click`
No description available.
**Exports:** HelpfulCommand, adk_services_options, deprecated_adk_services_options, eval_options, fast_api_common_options, validate_exclusive, web_options

## `google.adk.cli.conformance._generated_file_utils`
Loading utilities for conformance testing.
**Exports:** load_recorded_session, load_test_case

## `google.adk.cli.conformance._replay_validators`
Validation logic for conformance test replay mode.
**Exports:** ComparisonResult, compare_event, compare_events, compare_session

## `google.adk.cli.conformance.adk_web_server_client`
HTTP client for interacting with the ADK web server.
**Exports:** AdkWebServerClient

## `google.adk.cli.conformance.cli_record`
CLI commands for ADK conformance testing.
**Exports:** run_conformance_record

## `google.adk.cli.conformance.cli_test`
CLI implementation for ADK conformance testing.
**Exports:** ConformanceTestRunner, run_conformance_test

## `google.adk.cli.conformance.test_case`
No description available.
**Exports:** TestCase, TestSpec, UserMessage

## `google.adk.cli.fast_api`
No description available.
**Exports:** get_fast_api_app

## `google.adk.cli.plugins.recordings_plugin`
Recording plugin for ADK conformance testing.
**Exports:** RecordingsPlugin

## `google.adk.cli.plugins.recordings_schema`
Pydantic models for ADK recordings.
**Exports:** LlmRecording, Recording, Recordings, ToolRecording

## `google.adk.cli.plugins.replay_plugin`
Replay plugin for ADK conformance testing.
**Exports:** ReplayConfigError, ReplayPlugin, ReplayVerificationError

## `google.adk.cli.service_registry`
ADK Service Registry.
**Exports:** ServiceFactory, ServiceRegistry, get_service_registry, load_services_module

## `google.adk.cli.utils`
No description available.
**Exports:** create_empty_state, DotAdkFolder

## `google.adk.cli.utils.agent_change_handler`
File system event handler for agent changes to trigger hot reload for agents.
**Exports:** AgentChangeEventHandler

## `google.adk.cli.utils.agent_loader`
No description available.
**Exports:** AgentLoader

## `google.adk.cli.utils.base_agent_loader`
Base class for agent loaders.
**Exports:** BaseAgentLoader

## `google.adk.cli.utils.cleanup`
No description available.
**Exports:** close_runners

## `google.adk.cli.utils.common`
No description available.
**Exports:** BaseModel

## `google.adk.cli.utils.dot_adk_folder`
Helpers for managing an agent's `.adk` folder.
**Exports:** DotAdkFolder, dot_adk_folder_for_agent

## `google.adk.cli.utils.envs`
No description available.
**Exports:** load_dotenv_for_agent

## `google.adk.cli.utils.evals`
No description available.
**Exports:** GcsEvalManagers, convert_session_to_eval_invocations, create_gcs_eval_managers_from_uri

## `google.adk.cli.utils.local_storage`
Utilities for local .adk folder persistence.
**Exports:** PerAgentDatabaseSessionService, create_local_artifact_service, create_local_database_session_service, create_local_session_service

## `google.adk.cli.utils.logs`
No description available.
**Exports:** log_to_tmp_folder, setup_adk_logger

## `google.adk.cli.utils.service_factory`
No description available.
**Exports:** create_artifact_service_from_options, create_memory_service_from_options, create_session_service_from_options

## `google.adk.cli.utils.shared_value`
No description available.
**Exports:** SharedValue

## `google.adk.cli.utils.state`
No description available.
**Exports:** create_empty_state

## `google.adk.code_executors`
No description available.
**Exports:** BaseCodeExecutor, BuiltInCodeExecutor, CodeExecutorContext, UnsafeLocalCodeExecutor, VertexAiCodeExecutor, ContainerCodeExecutor, GkeCodeExecutor, AgentEngineSandboxCodeExecutor

## `google.adk.code_executors.agent_engine_sandbox_code_executor`
No description available.
**Exports:** AgentEngineSandboxCodeExecutor

## `google.adk.code_executors.base_code_executor`
No description available.
**Exports:** BaseCodeExecutor

## `google.adk.code_executors.built_in_code_executor`
No description available.
**Exports:** BuiltInCodeExecutor

## `google.adk.code_executors.code_execution_utils`
Utility functions for code execution.
**Exports:** CodeExecutionInput, CodeExecutionResult, CodeExecutionUtils, File

## `google.adk.code_executors.code_executor_context`
The persistent context used to configure the code executor.
**Exports:** CodeExecutorContext

## `google.adk.code_executors.unsafe_local_code_executor`
No description available.
**Exports:** UnsafeLocalCodeExecutor

## `google.adk.code_executors.vertex_ai_code_executor`
No description available.
**Exports:** VertexAiCodeExecutor

## `google.adk.errors.already_exists_error`
No description available.
**Exports:** AlreadyExistsError

## `google.adk.errors.input_validation_error`
No description available.
**Exports:** InputValidationError

## `google.adk.errors.not_found_error`
No description available.
**Exports:** NotFoundError

## `google.adk.evaluation`
No description available.
**Exports:** AgentEvaluator

## `google.adk.evaluation._eval_set_results_manager_utils`
No description available.
**Exports:** create_eval_set_result

## `google.adk.evaluation._eval_sets_manager_utils`
No description available.
**Exports:** add_eval_case_to_eval_set, delete_eval_case_from_eval_set, get_eval_case_from_eval_set, get_eval_set_from_app_and_id, update_eval_case_in_eval_set

## `google.adk.evaluation._retry_options_utils`
No description available.
**Exports:** EnsureRetryOptionsPlugin, add_default_retry_options_if_not_present

## `google.adk.evaluation.agent_evaluator`
No description available.
**Exports:** AgentEvaluator, load_json

## `google.adk.evaluation.app_details`
No description available.
**Exports:** AgentDetails, AppDetails

## `google.adk.evaluation.base_eval_service`
No description available.
**Exports:** BaseEvalService, EvaluateConfig, EvaluateRequest, InferenceConfig, InferenceRequest, InferenceResult, InferenceStatus

## `google.adk.evaluation.common`
No description available.
**Exports:** EvalBaseModel

## `google.adk.evaluation.conversation_scenarios`
No description available.
**Exports:** ConversationScenario, ConversationScenarios

## `google.adk.evaluation.eval_case`
No description available.
**Exports:** EvalCase, IntermediateData, Invocation, InvocationEvent, InvocationEvents, SessionInput, get_all_tool_calls, get_all_tool_calls_with_responses, get_all_tool_responses

## `google.adk.evaluation.eval_config`
No description available.
**Exports:** EvalConfig, get_eval_metrics_from_config, get_evaluation_criteria_or_default

## `google.adk.evaluation.eval_metrics`
No description available.
**Exports:** BaseCriterion, EvalMetric, EvalMetricResult, EvalMetricResultDetails, EvalMetricResultPerInvocation, EvalStatus, HallucinationsCriterion, Interval, JudgeModelOptions, LlmAsAJudgeCriterion, MetricInfo, MetricValueInfo, PrebuiltMetrics, RubricsBasedCriterion, ToolTrajectoryCriterion

## `google.adk.evaluation.eval_result`
No description available.
**Exports:** EvalCaseResult, EvalSetResult

## `google.adk.evaluation.eval_rubrics`
No description available.
**Exports:** Rubric, RubricContent, RubricScore

## `google.adk.evaluation.eval_set`
No description available.
**Exports:** EvalSet

## `google.adk.evaluation.eval_set_results_manager`
No description available.
**Exports:** EvalSetResultsManager

## `google.adk.evaluation.eval_sets_manager`
No description available.
**Exports:** EvalSetsManager

## `google.adk.evaluation.evaluation_constants`
No description available.
**Exports:** EvalConstants

## `google.adk.evaluation.evaluation_generator`
No description available.
**Exports:** EvalCaseResponses, EvaluationGenerator

## `google.adk.evaluation.evaluator`
No description available.
**Exports:** EvaluationResult, Evaluator, PerInvocationResult

## `google.adk.evaluation.final_response_match_v2`
No description available.
**Exports:** FinalResponseMatchV2Evaluator

## `google.adk.evaluation.gcs_eval_set_results_manager`
No description available.
**Exports:** GcsEvalSetResultsManager

## `google.adk.evaluation.gcs_eval_sets_manager`
No description available.
**Exports:** GcsEvalSetsManager

## `google.adk.evaluation.hallucinations_v1`
No description available.
**Exports:** EvaluationStep, HallucinationsV1Evaluator

## `google.adk.evaluation.in_memory_eval_sets_manager`
No description available.
**Exports:** InMemoryEvalSetsManager

## `google.adk.evaluation.llm_as_judge`
No description available.
**Exports:** AutoRaterScore, LlmAsJudge

## `google.adk.evaluation.llm_as_judge_utils`
No description available.
**Exports:** Label, get_average_rubric_score, get_eval_status, get_text_from_content, get_tool_calls_and_responses_as_json_str, get_tool_declarations_as_json_str

## `google.adk.evaluation.local_eval_set_results_manager`
No description available.
**Exports:** LocalEvalSetResultsManager

## `google.adk.evaluation.local_eval_sets_manager`
No description available.
**Exports:** LocalEvalSetsManager, convert_eval_set_to_pydantic_schema, load_eval_set_from_file

## `google.adk.evaluation.rubric_based_evaluator`
No description available.
**Exports:** AutoRaterResponseParser, DefaultAutoRaterResponseParser, InvocationResultsSummarizer, MajorityVotePerInvocationResultsAggregator, MeanInvocationResultsSummarizer, PerInvocationResultsAggregator, RubricBasedEvaluator, RubricResponse

## `google.adk.evaluation.rubric_based_final_response_quality_v1`
No description available.
**Exports:** RubricBasedFinalResponseQualityV1Evaluator

## `google.adk.evaluation.rubric_based_tool_use_quality_v1`
No description available.
**Exports:** RubricBasedToolUseV1Evaluator

## `google.adk.evaluation.safety_evaluator`
No description available.
**Exports:** SafetyEvaluatorV1

## `google.adk.evaluation.simulation.llm_backed_user_simulator`
No description available.
**Exports:** LlmBackedUserSimulator, LlmBackedUserSimulatorConfig

## `google.adk.evaluation.simulation.static_user_simulator`
No description available.
**Exports:** StaticUserSimulator

## `google.adk.evaluation.simulation.user_simulator`
No description available.
**Exports:** BaseUserSimulatorConfig, NextUserMessage, Status, UserSimulator

## `google.adk.evaluation.simulation.user_simulator_provider`
No description available.
**Exports:** UserSimulatorProvider

## `google.adk.evaluation.trajectory_evaluator`
No description available.
**Exports:** TrajectoryEvaluator

## `google.adk.events`
No description available.
**Exports:** Event, EventActions

## `google.adk.events.event`
No description available.
**Exports:** Event

## `google.adk.events.event_actions`
No description available.
**Exports:** EventActions, EventCompaction

## `google.adk.examples`
No description available.
**Exports:** BaseExampleProvider, Example, VertexAiExampleStore

## `google.adk.examples.base_example_provider`
No description available.
**Exports:** BaseExampleProvider

## `google.adk.examples.example`
No description available.
**Exports:** Example

## `google.adk.examples.example_util`
Utility functions for converting examples to a string that can be used in system instructions in the prompt.
**Exports:** build_example_si, convert_examples_to_text

## `google.adk.examples.vertex_ai_example_store`
No description available.
**Exports:** VertexAiExampleStore

## `google.adk.features`
No description available.
**Exports:** experimental, stable, working_in_progress, FeatureName, is_feature_enabled

## `google.adk.features._feature_decorator`
No description available.
**Exports:** experimental, stable, working_in_progress

## `google.adk.features._feature_registry`
No description available.
**Exports:** FeatureConfig, FeatureName, FeatureStage, is_feature_enabled

## `google.adk.flows.llm_flows._base_llm_processor`
Defines the processor interface used for BaseLlmFlow.
**Exports:** BaseLlmRequestProcessor, BaseLlmResponseProcessor

## `google.adk.flows.llm_flows._code_execution`
Handles Code Execution related logic.
**Exports:** DataFileUtil, get_content_as_bytes

## `google.adk.flows.llm_flows._output_schema_processor`
Handles output schema when tools are also present.
**Exports:** create_final_model_response_event, get_structured_model_response

## `google.adk.flows.llm_flows.audio_cache_manager`
No description available.
**Exports:** AudioCacheConfig, AudioCacheManager

## `google.adk.flows.llm_flows.audio_transcriber`
No description available.
**Exports:** AudioTranscriber

## `google.adk.flows.llm_flows.auto_flow`
Implementation of AutoFlow.
**Exports:** AutoFlow

## `google.adk.flows.llm_flows.base_llm_flow`
No description available.
**Exports:** BaseLlmFlow

## `google.adk.flows.llm_flows.context_cache_processor`
Context cache processor for LLM requests.
**Exports:** ContextCacheRequestProcessor

## `google.adk.flows.llm_flows.functions`
Handles function calling for LLM flow.
**Exports:** deep_merge_dicts, find_matching_function_call, generate_auth_event, generate_client_function_call_id, generate_request_confirmation_event, get_long_running_function_calls, handle_function_call_list_async, handle_function_calls_async, handle_function_calls_live, merge_parallel_function_response_events, populate_client_function_call_id, remove_client_function_call_id

## `google.adk.flows.llm_flows.single_flow`
Implementation of single flow.
**Exports:** SingleFlow

## `google.adk.flows.llm_flows.transcription_manager`
No description available.
**Exports:** TranscriptionManager

## `google.adk.memory`
No description available.
**Exports:** BaseMemoryService, InMemoryMemoryService, VertexAiMemoryBankService, VertexAiRagMemoryService

## `google.adk.memory._utils`
No description available.
**Exports:** format_timestamp

## `google.adk.memory.base_memory_service`
No description available.
**Exports:** BaseMemoryService, SearchMemoryResponse

## `google.adk.memory.in_memory_memory_service`
No description available.
**Exports:** InMemoryMemoryService

## `google.adk.memory.memory_entry`
No description available.
**Exports:** MemoryEntry

## `google.adk.memory.vertex_ai_memory_bank_service`
No description available.
**Exports:** VertexAiMemoryBankService

## `google.adk.memory.vertex_ai_rag_memory_service`
No description available.
**Exports:** VertexAiRagMemoryService

## `google.adk.models`
Defines the interface to support a model.
**Exports:** BaseLlm, Gemini, Gemma, LLMRegistry, LiteLlm

## `google.adk.models.apigee_llm`
No description available.
**Exports:** ApigeeLlm

## `google.adk.models.base_llm`
No description available.
**Exports:** BaseLlm

## `google.adk.models.base_llm_connection`
No description available.
**Exports:** BaseLlmConnection

## `google.adk.models.cache_metadata`
No description available.
**Exports:** CacheMetadata

## `google.adk.models.gemini_context_cache_manager`
Manages context cache lifecycle for Gemini models.
**Exports:** GeminiContextCacheManager

## `google.adk.models.gemini_llm_connection`
No description available.
**Exports:** GeminiLlmConnection

## `google.adk.models.gemma_llm`
No description available.
**Exports:** Gemma, GemmaFunctionCallModel

## `google.adk.models.google_llm`
No description available.
**Exports:** Gemini

## `google.adk.models.lite_llm`
No description available.
**Exports:** ChatCompletionFileUrlObject, FunctionChunk, LiteLLMClient, LiteLlm, ReasoningChunk, TextChunk, UsageMetadataChunk

## `google.adk.models.llm_request`
No description available.
**Exports:** LlmRequest

## `google.adk.models.llm_response`
No description available.
**Exports:** LlmResponse

## `google.adk.models.registry`
The registry class for model.
**Exports:** LLMRegistry

## `google.adk.planners`
No description available.
**Exports:** BasePlanner, BuiltInPlanner, PlanReActPlanner

## `google.adk.planners.base_planner`
No description available.
**Exports:** BasePlanner

## `google.adk.planners.built_in_planner`
No description available.
**Exports:** BuiltInPlanner

## `google.adk.planners.plan_re_act_planner`
No description available.
**Exports:** PlanReActPlanner

## `google.adk.platform.thread`
No description available.
**Exports:** create_thread

## `google.adk.plugins`
No description available.
**Exports:** BasePlugin, LoggingPlugin, PluginManager, ReflectAndRetryToolPlugin

## `google.adk.plugins.base_plugin`
No description available.
**Exports:** BasePlugin

## `google.adk.plugins.bigquery_agent_analytics_plugin`
No description available.
**Exports:** BigQueryAgentAnalyticsPlugin, BigQueryLoggerConfig, to_arrow_schema

## `google.adk.plugins.context_filter_plugin`
No description available.
**Exports:** ContextFilterPlugin

## `google.adk.plugins.global_instruction_plugin`
No description available.
**Exports:** GlobalInstructionPlugin

## `google.adk.plugins.logging_plugin`
No description available.
**Exports:** LoggingPlugin

## `google.adk.plugins.multimodal_tool_results_plugin`
No description available.
**Exports:** MultimodalToolResultsPlugin

## `google.adk.plugins.plugin_manager`
No description available.
**Exports:** PluginManager

## `google.adk.plugins.reflect_retry_tool_plugin`
No description available.
**Exports:** ReflectAndRetryToolPlugin, ToolFailureResponse, TrackingScope

## `google.adk.plugins.save_files_as_artifacts_plugin`
No description available.
**Exports:** SaveFilesAsArtifactsPlugin

## `google.adk.runners`
No description available.
**Exports:** InMemoryRunner, Runner

## `google.adk.sessions`
No description available.
**Exports:** BaseSessionService, DatabaseSessionService, InMemorySessionService, Session, State, VertexAiSessionService

## `google.adk.sessions._session_util`
Utility functions for session service.
**Exports:** decode_model, extract_state_delta

## `google.adk.sessions.base_session_service`
No description available.
**Exports:** BaseSessionService, GetSessionConfig, ListSessionsResponse

## `google.adk.sessions.database_session_service`
No description available.
**Exports:** Base, DatabaseSessionService, DynamicJSON, DynamicPickleType, PreciseTimestamp, StorageAppState, StorageEvent, StorageSession, StorageUserState, set_sqlite_pragma

## `google.adk.sessions.in_memory_session_service`
No description available.
**Exports:** InMemorySessionService

## `google.adk.sessions.migrate_from_sqlalchemy_sqlite`
Migration script from SQLAlchemy SQLite to the new SQLite JSON schema.
**Exports:** migrate

## `google.adk.sessions.session`
No description available.
**Exports:** Session

## `google.adk.sessions.sqlite_session_service`
No description available.
**Exports:** SqliteSessionService

## `google.adk.sessions.state`
No description available.
**Exports:** State

## `google.adk.sessions.vertex_ai_session_service`
No description available.
**Exports:** VertexAiSessionService

## `google.adk.telemetry`
No description available.
**Exports:** trace_call_llm, trace_merged_tool_calls, trace_send_data, trace_tool_call, tracer

## `google.adk.telemetry.google_cloud`
No description available.
**Exports:** get_gcp_exporters, get_gcp_resource

## `google.adk.telemetry.setup`
No description available.
**Exports:** OTelHooks, maybe_set_otel_providers

## `google.adk.telemetry.tracing`
No description available.
**Exports:** trace_agent_invocation, trace_call_llm, trace_merged_tool_calls, trace_send_data, trace_tool_call

## `google.adk.tools`
No description available.
**Exports:** AuthToolArguments, AgentTool, APIHubToolset, BaseTool, DiscoveryEngineSearchTool, enterprise_web_search, ExampleTool, exit_loop, FunctionTool, get_user_choice, google_maps_grounding, google_search, load_artifacts, load_memory, LongRunningFunctionTool, preload_memory, ToolContext, transfer_to_agent, TransferToAgentTool, url_context, VertexAiSearchTool, MCPToolset, McpToolset, ApiRegistry

## `google.adk.tools._automatic_function_calling_util`
No description available.
**Exports:** build_function_declaration, build_function_declaration_for_langchain, build_function_declaration_for_params_for_crewai, build_function_declaration_util, from_function_with_options

## `google.adk.tools._forwarding_artifact_service`
No description available.
**Exports:** ForwardingArtifactService

## `google.adk.tools._google_credentials`
No description available.
**Exports:** BaseGoogleCredentialsConfig, GoogleCredentialsManager

## `google.adk.tools._memory_entry_utils`
No description available.
**Exports:** extract_text

## `google.adk.tools.agent_tool`
No description available.
**Exports:** AgentTool, AgentToolConfig

## `google.adk.tools.api_registry`
No description available.
**Exports:** ApiRegistry

## `google.adk.tools.apihub_tool`
No description available.
**Exports:** APIHubToolset

## `google.adk.tools.apihub_tool.apihub_toolset`
No description available.
**Exports:** APIHubToolset

## `google.adk.tools.apihub_tool.clients.apihub_client`
No description available.
**Exports:** APIHubClient, BaseAPIHubClient

## `google.adk.tools.apihub_tool.clients.secret_client`
No description available.
**Exports:** SecretManagerClient

## `google.adk.tools.application_integration_tool`
No description available.
**Exports:** ApplicationIntegrationToolset, IntegrationConnectorTool

## `google.adk.tools.application_integration_tool.application_integration_toolset`
No description available.
**Exports:** ApplicationIntegrationToolset

## `google.adk.tools.application_integration_tool.integration_connector_tool`
No description available.
**Exports:** IntegrationConnectorTool

## `google.adk.tools.authenticated_function_tool`
No description available.
**Exports:** AuthenticatedFunctionTool

## `google.adk.tools.base_authenticated_tool`
No description available.
**Exports:** BaseAuthenticatedTool

## `google.adk.tools.base_tool`
No description available.
**Exports:** BaseTool

## `google.adk.tools.base_toolset`
No description available.
**Exports:** BaseToolset, ToolPredicate

## `google.adk.tools.bigquery`
BigQuery Tools (Experimental).
**Exports:** BigQueryToolset, BigQueryCredentialsConfig

## `google.adk.tools.bigquery.bigquery_credentials`
No description available.
**Exports:** BigQueryCredentialsConfig

## `google.adk.tools.bigquery.bigquery_toolset`
No description available.
**Exports:** BigQueryToolset

## `google.adk.tools.bigquery.client`
No description available.
**Exports:** get_bigquery_client

## `google.adk.tools.bigquery.config`
No description available.
**Exports:** BigQueryToolConfig, WriteMode

## `google.adk.tools.bigquery.data_insights_tool`
No description available.
**Exports:** ask_data_insights

## `google.adk.tools.bigquery.metadata_tool`
No description available.
**Exports:** get_dataset_info, get_job_info, get_table_info, list_dataset_ids, list_table_ids

## `google.adk.tools.bigquery.query_tool`
No description available.
**Exports:** analyze_contribution, detect_anomalies, execute_sql, forecast, get_execute_sql

## `google.adk.tools.bigtable`
Bigtable Tools (Experimental).
**Exports:** BigtableToolset, BigtableCredentialsConfig

## `google.adk.tools.bigtable.bigtable_credentials`
No description available.
**Exports:** BigtableCredentialsConfig

## `google.adk.tools.bigtable.bigtable_toolset`
No description available.
**Exports:** BigtableToolset

## `google.adk.tools.bigtable.client`
No description available.
**Exports:** get_bigtable_admin_client, get_bigtable_data_client

## `google.adk.tools.bigtable.metadata_tool`
No description available.
**Exports:** get_instance_info, get_table_info, list_instances, list_tables

## `google.adk.tools.bigtable.query_tool`
No description available.
**Exports:** execute_sql

## `google.adk.tools.bigtable.settings`
No description available.
**Exports:** BigtableToolSettings

## `google.adk.tools.computer_use.base_computer`
No description available.
**Exports:** BaseComputer, ComputerEnvironment, ComputerState

## `google.adk.tools.computer_use.computer_use_tool`
No description available.
**Exports:** ComputerUseTool

## `google.adk.tools.computer_use.computer_use_toolset`
No description available.
**Exports:** ComputerUseToolset

## `google.adk.tools.discovery_engine_search_tool`
No description available.
**Exports:** DiscoveryEngineSearchTool

## `google.adk.tools.enterprise_search_tool`
No description available.
**Exports:** EnterpriseWebSearchTool

## `google.adk.tools.example_tool`
No description available.
**Exports:** ExampleTool, ExampleToolConfig

## `google.adk.tools.exit_loop_tool`
No description available.
**Exports:** exit_loop

## `google.adk.tools.function_tool`
No description available.
**Exports:** FunctionTool

## `google.adk.tools.get_user_choice_tool`
No description available.
**Exports:** get_user_choice

## `google.adk.tools.google_api_tool`
Auto-generated tools and toolsets for Google APIs.
**Exports:** BigQueryToolset, CalendarToolset, GmailToolset, YoutubeToolset, SlidesToolset, SheetsToolset, DocsToolset, GoogleApiToolset, GoogleApiTool

## `google.adk.tools.google_api_tool.google_api_tool`
No description available.
**Exports:** GoogleApiTool

## `google.adk.tools.google_api_tool.google_api_toolset`
No description available.
**Exports:** GoogleApiToolset

## `google.adk.tools.google_api_tool.google_api_toolsets`
No description available.
**Exports:** BigQueryToolset, CalendarToolset, DocsToolset, GmailToolset, SheetsToolset, SlidesToolset, YoutubeToolset

## `google.adk.tools.google_api_tool.googleapi_to_openapi_converter`
No description available.
**Exports:** GoogleApiToOpenApiConverter, main

## `google.adk.tools.google_maps_grounding_tool`
No description available.
**Exports:** GoogleMapsGroundingTool

## `google.adk.tools.google_search_agent_tool`
No description available.
**Exports:** GoogleSearchAgentTool, create_google_search_agent

## `google.adk.tools.google_search_tool`
No description available.
**Exports:** GoogleSearchTool

## `google.adk.tools.google_tool`
No description available.
**Exports:** GoogleTool

## `google.adk.tools.load_artifacts_tool`
No description available.
**Exports:** LoadArtifactsTool

## `google.adk.tools.load_memory_tool`
No description available.
**Exports:** LoadMemoryResponse, LoadMemoryTool, load_memory

## `google.adk.tools.load_web_page`
Tool for web browse.
**Exports:** load_web_page

## `google.adk.tools.long_running_tool`
No description available.
**Exports:** LongRunningFunctionTool

## `google.adk.tools.mcp_tool`
No description available.
**Exports:** adk_to_mcp_tool_type, gemini_to_json_schema, McpTool, MCPTool, McpToolset, MCPToolset, SseConnectionParams, StdioConnectionParams, StreamableHTTPConnectionParams

## `google.adk.tools.mcp_tool.conversion_utils`
No description available.
**Exports:** adk_to_mcp_tool_type, gemini_to_json_schema

## `google.adk.tools.mcp_tool.mcp_session_manager`
No description available.
**Exports:** MCPSessionManager, SseConnectionParams, SseServerParams, StdioConnectionParams, StreamableHTTPConnectionParams, StreamableHTTPServerParams, retry_on_errors

## `google.adk.tools.mcp_tool.mcp_tool`
No description available.
**Exports:** MCPTool, McpTool

## `google.adk.tools.mcp_tool.mcp_toolset`
No description available.
**Exports:** MCPToolset, McpToolset, McpToolsetConfig

## `google.adk.tools.openapi_tool`
No description available.
**Exports:** OpenAPIToolset, RestApiTool

## `google.adk.tools.openapi_tool.auth`
No description available.
**Exports:** auth_helpers

## `google.adk.tools.openapi_tool.auth.auth_helpers`
No description available.
**Exports:** OpenIdConfig, credential_to_param, dict_to_auth_scheme, openid_dict_to_scheme_credential, openid_url_to_scheme_credential, service_account_dict_to_scheme_credential, service_account_scheme_credential, token_to_scheme_credential

## `google.adk.tools.openapi_tool.auth.credential_exchangers`
No description available.
**Exports:** AutoAuthCredentialExchanger, BaseAuthCredentialExchanger, OAuth2CredentialExchanger, ServiceAccountCredentialExchanger

## `google.adk.tools.openapi_tool.auth.credential_exchangers.auto_auth_credential_exchanger`
No description available.
**Exports:** AutoAuthCredentialExchanger

## `google.adk.tools.openapi_tool.auth.credential_exchangers.base_credential_exchanger`
No description available.
**Exports:** AuthCredentialMissingError, BaseAuthCredentialExchanger

## `google.adk.tools.openapi_tool.auth.credential_exchangers.oauth2_exchanger`
Credential fetcher for OpenID Connect.
**Exports:** OAuth2CredentialExchanger

## `google.adk.tools.openapi_tool.auth.credential_exchangers.service_account_exchanger`
Credential fetcher for Google Service Account.
**Exports:** ServiceAccountCredentialExchanger

## `google.adk.tools.openapi_tool.common`
No description available.
**Exports:** common

## `google.adk.tools.openapi_tool.common.common`
No description available.
**Exports:** ApiParameter, PydocHelper, TypeHintHelper, rename_python_keywords

## `google.adk.tools.openapi_tool.openapi_spec_parser`
No description available.
**Exports:** OpenApiSpecParser, OperationEndpoint, ParsedOperation, OpenAPIToolset, OperationParser, RestApiTool, snake_to_lower_camel, AuthPreparationState, ToolAuthHandler

## `google.adk.tools.openapi_tool.openapi_spec_parser.openapi_spec_parser`
No description available.
**Exports:** OpenApiSpecParser, OperationEndpoint, ParsedOperation

## `google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset`
No description available.
**Exports:** OpenAPIToolset

## `google.adk.tools.openapi_tool.openapi_spec_parser.operation_parser`
No description available.
**Exports:** OperationParser

## `google.adk.tools.openapi_tool.openapi_spec_parser.rest_api_tool`
No description available.
**Exports:** RestApiTool, snake_to_lower_camel

## `google.adk.tools.openapi_tool.openapi_spec_parser.tool_auth_handler`
No description available.
**Exports:** AuthPreparationResult, ToolAuthHandler, ToolContextCredentialStore

## `google.adk.tools.preload_memory_tool`
No description available.
**Exports:** PreloadMemoryTool

## `google.adk.tools.retrieval`
No description available.
**Exports:** BaseRetrievalTool, FilesRetrieval, LlamaIndexRetrieval, VertexAiRagRetrieval

## `google.adk.tools.retrieval.base_retrieval_tool`
No description available.
**Exports:** BaseRetrievalTool

## `google.adk.tools.retrieval.llama_index_retrieval`
Provides data for the agent.
**Exports:** LlamaIndexRetrieval

## `google.adk.tools.retrieval.vertex_ai_rag_retrieval`
A retrieval tool that uses Vertex AI RAG to retrieve data.
**Exports:** VertexAiRagRetrieval

## `google.adk.tools.set_model_response_tool`
Tool for setting model response when using output_schema with other tools.
**Exports:** SetModelResponseTool

## `google.adk.tools.spanner`
Spanner Tools (Experimental).
**Exports:** SpannerToolset, SpannerCredentialsConfig

## `google.adk.tools.spanner.client`
No description available.
**Exports:** get_spanner_client

## `google.adk.tools.spanner.metadata_tool`
No description available.
**Exports:** get_table_schema, list_named_schemas, list_table_index_columns, list_table_indexes, list_table_names

## `google.adk.tools.spanner.query_tool`
No description available.
**Exports:** execute_sql

## `google.adk.tools.spanner.search_tool`
No description available.
**Exports:** similarity_search, vector_store_similarity_search

## `google.adk.tools.spanner.settings`
No description available.
**Exports:** Capabilities, SpannerToolSettings, SpannerVectorStoreSettings

## `google.adk.tools.spanner.spanner_credentials`
No description available.
**Exports:** SpannerCredentialsConfig

## `google.adk.tools.spanner.spanner_toolset`
No description available.
**Exports:** SpannerToolset

## `google.adk.tools.spanner.utils`
No description available.
**Exports:** embed_contents, execute_sql

## `google.adk.tools.tool_configs`
No description available.
**Exports:** BaseToolConfig, ToolArgsConfig, ToolConfig

## `google.adk.tools.tool_confirmation`
No description available.
**Exports:** ToolConfirmation

## `google.adk.tools.tool_context`
No description available.
**Exports:** ToolContext

## `google.adk.tools.transfer_to_agent_tool`
No description available.
**Exports:** TransferToAgentTool, transfer_to_agent

## `google.adk.tools.url_context_tool`
No description available.
**Exports:** UrlContextTool

## `google.adk.tools.vertex_ai_search_tool`
No description available.
**Exports:** VertexAiSearchTool

## `google.adk.utils._client_labels_utils`
No description available.
**Exports:** client_label_context, get_client_labels

## `google.adk.utils._debug_output`
No description available.
**Exports:** print_event

## `google.adk.utils.cache_performance_analyzer`
Cache performance analysis utilities for ADK context caching system.
**Exports:** CachePerformanceAnalyzer

## `google.adk.utils.context_utils`
Utilities for ADK context management.
**Exports:** Aclosing

## `google.adk.utils.env_utils`
Utilities for environment variable handling.
**Exports:** is_env_enabled

## `google.adk.utils.feature_decorator`
No description available.
**Exports:** experimental, working_in_progress

## `google.adk.utils.instructions_utils`
No description available.
**Exports:** inject_session_state

## `google.adk.utils.model_name_utils`
Utilities for model name validation and parsing.
**Exports:** extract_model_name, is_gemini_1_model, is_gemini_2_or_above, is_gemini_model

## `google.adk.utils.output_schema_utils`
Utilities for Output Schema.
**Exports:** can_use_output_schema_with_tools

## `google.adk.utils.streaming_utils`
No description available.
**Exports:** StreamingResponseAggregator

## `google.adk.utils.variant_utils`
Utilities for Google LLM variants.
**Exports:** GoogleLLMVariant, get_google_llm_variant

## `google.adk.utils.vertex_ai_utils`
Utilities for Vertex AI. Includes helper functions for Express Mode.
**Exports:** get_express_mode_api_key

## `google.adk.utils.yaml_utils`
No description available.
**Exports:** dump_pydantic_to_yaml, load_yaml_file
