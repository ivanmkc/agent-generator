# Retrieval Dataset Analysis Report

## 1. Executive Summary

- **Total Cases Verified:** 5
- **Total Candidates Analyzed:** 175
- **Average Zero-Context Success Rate:** 46.67%

This report details the empirical relevance of documentation for each benchmark query, identifying 'Critical' documents (high Delta P) and 'Toxic' distractors.

## 2. Case Breakdown

### Case: `configure_adk_features_mc:which_is_the_correct_import_statement_for_the_runn`
**Query:** Which is the correct import statement for the `Runner` class?

- **Zero-Context Success:** 0.00%
- **Final Max Uncertainty (SE):** 0.0902

| Status   |   Delta P | Source       |   Trials (In) | Document FQN                                                                                 |
|----------|-----------|--------------|---------------|----------------------------------------------------------------------------------------------|
| ⚪ Noise |         0 | gold_mined   |            17 | google.adk.runners                                                                           |
| ⚪ Noise |         0 | gold_mined   |            18 | google.adk.runners.Runner                                                                    |
| ⚪ Noise |         0 | retrieved    |            21 | google.adk.runners.Runner.execute                                                            |
| ⚪ Noise |         0 | retrieved    |            19 | google.adk.runners.Runner.close                                                              |
| ⚪ Noise |         0 | retrieved    |            18 | google.adk.runners.InMemoryRunner                                                            |
| ⚪ Noise |         0 | retrieved    |            23 | google.adk.a2a.utils.agent_to_a2a.create_runner                                              |
| ⚪ Noise |         0 | retrieved    |            21 | google.adk.runners.Runner.run                                                                |
| ⚪ Noise |         0 | retrieved    |            25 | google.adk.cli.adk_web_server.AdkWebServer.get_runner_async                                  |
| ⚪ Noise |         0 | retrieved    |            26 | google.adk.agents.run_config.RunConfig                                                       |
| ⚪ Noise |         0 | retrieved    |            19 | google.adk.code_executors.built_in_code_executor                                             |
| ⚪ Noise |         0 | retrieved    |            17 | google.adk.runners.Runner.run_async                                                          |
| ⚪ Noise |         0 | retrieved    |            21 | google.adk.code_executors.base_code_executor                                                 |
| ⚪ Noise |         0 | retrieved    |            22 | google.adk.plugins.logging_plugin.LoggingPlugin.on_event_callback                            |
| ⚪ Noise |         0 | retrieved    |            21 | google.adk.a2a.converters.request_converter.AgentRunRequest                                  |
| ⚪ Noise |         0 | random_noise |            17 | google.adk.sessions.database_session_service.StorageSession.update_timestamp_tz              |
| ⚪ Noise |         0 | random_noise |            21 | vertexai.preview.evaluation.constants.Metric                                                 |
| ⚪ Noise |         0 | random_noise |            25 | vertexai.evaluation.metrics.pointwise_metric.Comet                                           |
| ⚪ Noise |         0 | random_noise |            16 | google.adk.tools.authenticated_function_tool.AuthenticatedFunctionTool.run_async             |
| ⚪ Noise |         0 | random_noise |            16 | google.adk.plugins.reflect_retry_tool_plugin.ToolFailureResponse                             |
| ⚪ Noise |         0 | random_noise |            24 | vertexai.resources.preview.feature_store.feature                                             |
| ⚪ Noise |         0 | random_noise |            17 | google.genai.models.AsyncModels.generate_content_stream                                      |
| ⚪ Noise |         0 | random_noise |            22 | google.adk.agents.config_agent_utils.resolve_code_reference                                  |
| ⚪ Noise |         0 | random_noise |            19 | vertexai.resources.preview.feature_store.utils.get_feature_online_store_name                 |
| ⚪ Noise |         0 | random_noise |            21 | google.genai.types.DeleteResourceJob                                                         |
| ⚪ Noise |         0 | random_noise |            22 | google.genai.types.Part.as_image                                                             |
| ⚪ Noise |         0 | random_noise |            18 | vertexai.preview.reasoning_engines.templates.llama_index.LlamaIndexQueryPipelineAgent.set_up |
| ⚪ Noise |         0 | random_noise |            21 | google.adk.cli.conformance.cli_test.run_conformance_test                                     |
| ⚪ Noise |         0 | random_noise |            12 | google.adk.sessions.base_session_service.ListSessionsResponse                                |
| ⚪ Noise |         0 | random_noise |            22 | google.adk.agents.sequential_agent.SequentialAgent._run_async_impl                           |
| ⚪ Noise |         0 | random_noise |            19 | google.genai.types.Schema.copy_schema_fields                                                 |
| ⚪ Noise |         0 | random_noise |            19 | google.genai.types.JobState                                                                  |
| ⚪ Noise |         0 | random_noise |            19 | google.adk.evaluation.simulation.llm_backed_user_simulator.LlmBackedUserSimulator            |
| ⚪ Noise |         0 | random_noise |            21 | vertexai.evaluation.metrics.pairwise_metric                                                  |
| ⚪ Noise |         0 | random_noise |            19 | google.adk.runners.Runner.run_debug                                                          |

---

### Case: `configure_adk_features_mc:you_need_to_inspect_an_event_object_which_import_a`
**Query:** You need to inspect an `Event` object. Which import allows you to reference the `Event` class for type hinting?

- **Zero-Context Success:** 100.00%
- **Final Max Uncertainty (SE):** 0.0910

| Status     |   Delta P | Source       |   Trials (In) | Document FQN                                                                                          |
|------------|-----------|--------------|---------------|-------------------------------------------------------------------------------------------------------|
| yg Helpful |      0.11 | retrieved    |            22 | google.adk.evaluation.eval_case.InvocationEvents                                                      |
| yg Helpful |      0.11 | retrieved    |            22 | google.adk.sessions.database_session_service.StorageEvent.from_event                                  |
| yg Helpful |      0.11 | retrieved    |            23 | google.adk.apps.base_events_summarizer.BaseEventsSummarizer                                           |
| yg Helpful |      0.11 | random_noise |            22 | google.genai.caches.AsyncCaches.get                                                                   |
| yg Helpful |      0.11 | random_noise |            22 | google.genai.chats.AsyncChats.create                                                                  |
| yg Helpful |      0.11 | random_noise |            22 | google.adk.code_executors.code_execution_utils                                                        |
| yg Helpful |      0.1  | retrieved    |            20 | google.adk.a2a.converters.event_converter                                                             |
| yg Helpful |      0.1  | random_noise |            21 | vertexai.preview.reasoning_engines.templates.langgraph.LanggraphAgent.clone                           |
| yg Helpful |      0.09 | random_noise |            19 | google.genai.types.VideoGenerationMaskMode                                                            |
| yg Helpful |      0.08 | retrieved    |            16 | google.adk.events.event.Event                                                                         |
| yg Helpful |      0.08 | random_noise |            15 | google.adk.cli.fast_api.register_processors                                                           |
| yg Helpful |      0.07 | random_noise |            13 | google.genai.types.VertexAISearchDict                                                                 |
| ⚪ Noise   |      0.03 | random_noise |            26 | google.genai.types.InlinedRequestDict                                                                 |
| ⚪ Noise   |      0.02 | retrieved    |            24 | google.adk.cli.adk_web_server.GetEventGraphResult                                                     |
| ⚪ Noise   |      0.02 | retrieved    |            24 | google.adk.sessions.database_session_service.StorageEvent.to_event                                    |
| ⚪ Noise   |      0.02 | retrieved    |            25 | google.adk.tools.openapi_tool.common.common.TypeHintHelper.get_type_value                             |
| ⚪ Noise   |      0.02 | random_noise |            25 | google.genai.types.Video.save                                                                         |
| ⚪ Noise   |      0.01 | gold_mined   |            22 | google.adk.models                                                                                     |
| ⚪ Noise   |      0.01 | retrieved    |            23 | google.adk.events.event_actions.EventActions                                                          |
| ⚪ Noise   |      0.01 | retrieved    |            22 | google.adk.tools.openapi_tool.common.common.TypeHintHelper                                            |
| ⚪ Noise   |      0.01 | retrieved    |            22 | google.adk.events.event_actions.EventCompaction                                                       |
| ⚪ Noise   |      0.01 | retrieved    |            22 | google.adk.cli.adk_web_server.AdkWebServer.event_generator                                            |
| ⚪ Noise   |      0.01 | retrieved    |            23 | google.adk.evaluation.eval_case.InvocationEvent                                                       |
| ⚪ Noise   |      0.01 | random_noise |            22 | google.adk.evaluation.eval_result.EvalCaseResult                                                      |
| ⚪ Noise   |      0.01 | random_noise |            22 | google.adk.cli.built_in_agents.adk_agent_builder_assistant.AgentBuilderAssistant.instruction_provider |
| ⚪ Noise   |      0.01 | random_noise |            22 | google.adk.cli.fast_api.get_agent_builder                                                             |
| ⚪ Noise   |      0    | random_noise |            21 | google.adk.sessions.sqlite_session_service.SqliteSessionService.get_session                           |
| ⚪ Noise   |     -0.01 | random_noise |            18 | google.adk.models.llm_request.LlmRequest.append_tools                                                 |
| ⚪ Noise   |     -0.01 | random_noise |            18 | google.adk.runners.Runner.run_live                                                                    |
| ⚪ Noise   |     -0.02 | gold_mined   |            16 | google.adk.events.event                                                                               |
| ⚪ Noise   |     -0.08 | retrieved    |            24 | google.adk.events.event_actions                                                                       |
| ⚪ Noise   |     -0.08 | random_noise |            26 | google.genai.types.FileSource                                                                         |
| ⚪ Noise   |     -0.08 | random_noise |            24 | vertexai.rag.rag_data.add_inline_citations_and_references                                             |
| ⚪ Noise   |     -0.09 | random_noise |            23 | google.genai.types.FileSearchStore                                                                    |
| ⚪ Noise   |     -0.1  | random_noise |            21 | google.adk.plugins.base_plugin.BasePlugin.before_agent_callback                                       |
| ❌ Toxic   |     -0.11 | retrieved    |            19 | google.adk.tools.openapi_tool.common.common.TypeHintHelper.get_type_hint                              |

---

### Case: `configure_adk_features_mc:when_calling_runner_run_async_which_parameter_is_u`
**Query:** When calling `runner.run_async()`, which parameter is used to pass the user's input message?

- **Zero-Context Success:** 0.00%
- **Final Max Uncertainty (SE):** 0.1337

| Status      |   Delta P | Source       |   Trials (In) | Document FQN                                                                       |
|-------------|-----------|--------------|---------------|------------------------------------------------------------------------------------|
| ✅ Critical |      0.93 | retrieved    |            30 | google.adk.runners.Runner.run_async                                                |
| ✅ Critical |      0.3  | retrieved    |            35 | google.adk.runners.Runner.run                                                      |
| yg Helpful  |      0.2  | random_noise |            32 | google.genai.file_search_stores.AsyncFileSearchStores.import_file                  |
| yg Helpful  |      0.18 | retrieved    |            25 | google.adk.agents.base_agent.BaseAgent._run_async_impl                             |
| yg Helpful  |      0.16 | retrieved    |            35 | vertexai.preview.reasoning_engines.templates.adk.AdkApp.async_stream_query         |
| yg Helpful  |      0.16 | random_noise |            31 | google.adk.agents.transcription_entry                                              |
| yg Helpful  |      0.14 | retrieved    |            28 | google.genai.chats.AsyncChat.send_message                                          |
| yg Helpful  |      0.14 | random_noise |            26 | google.adk.evaluation.hallucinations_v1.EvaluationStep                             |
| yg Helpful  |      0.11 | random_noise |            27 | google.genai.types.CustomMetadataDict                                              |
| yg Helpful  |      0.11 | random_noise |            27 | google.genai.caches.Caches.list                                                    |
| yg Helpful  |      0.11 | random_noise |            25 | google.adk.telemetry.google_cloud.get_gcp_resource                                 |
| yg Helpful  |      0.1  | random_noise |            31 | google.genai.types.GetOperationConfigDict                                          |
| yg Helpful  |      0.09 | retrieved    |            33 | google.adk.plugins.base_plugin.BasePlugin.on_user_message_callback                 |
| ⚪ Noise    |      0.04 | random_noise |            27 | vertexai.resources.preview.feature_store.feature_online_store                      |
| ⚪ Noise    |      0.03 | random_noise |            31 | google.genai.types.InlinedResponse                                                 |
| ⚪ Noise    |     -0    | random_noise |            32 | vertexai.preview.rag.rag_data.delete_corpus                                        |
| ⚪ Noise    |     -0.01 | random_noise |            36 | google.adk.auth.credential_manager.CredentialManager.register_credential_exchanger |
| ⚪ Noise    |     -0.01 | random_noise |            36 | google.adk.flows.llm_flows.audio_cache_manager.AudioCacheConfig                    |
| ⚪ Noise    |     -0.02 | retrieved    |            25 | vertexai.agent_engines.templates.adk.AdkApp.async_stream_query                     |
| ⚪ Noise    |     -0.03 | retrieved    |            29 | vertexai.preview.reasoning_engines.templates.adk.AdkApp.stream_query               |
| ⚪ Noise    |     -0.03 | random_noise |            29 | google.genai.types.StyleReferenceImage                                             |
| ⚪ Noise    |     -0.04 | random_noise |            33 | google.adk.tools.agent_tool.AgentToolConfig                                        |
| ⚪ Noise    |     -0.06 | retrieved    |            28 | google.adk.runners.Runner.run_debug                                                |
| ⚪ Noise    |     -0.06 | retrieved    |            28 | google.adk.runners.Runner                                                          |
| ⚪ Noise    |     -0.08 | retrieved    |            34 | google.adk.agents.base_agent.BaseAgent.run_async                                   |
| ⚪ Noise    |     -0.08 | retrieved    |            36 | google.adk.runners.Runner.run_live                                                 |
| ⚪ Noise    |     -0.08 | random_noise |            34 | google.genai.types.GetCachedContentConfig                                          |
| ⚪ Noise    |     -0.09 | random_noise |            25 | google.adk.evaluation.response_evaluator.ResponseEvaluator                         |
| ⚪ Noise    |     -0.09 | random_noise |            25 | google.genai.types.BatchJobDestination                                             |
| ⚪ Noise    |     -0.09 | random_noise |            25 | google.adk.flows.llm_flows.base_llm_flow.BaseLlmFlow                               |
| ❌ Toxic    |     -0.11 | retrieved    |            33 | google.genai.live.AsyncSession.send                                                |
| ❌ Toxic    |     -0.11 | random_noise |            33 | google.genai.types.UpscaleImageConfigDict                                          |
| ❌ Toxic    |     -0.12 | random_noise |            37 | google.adk.evaluation.eval_set_results_manager.EvalSetResultsManager               |
| ❌ Toxic    |     -0.16 | retrieved    |            21 | vertexai.agent_engines.templates.adk.AdkApp.stream_query                           |
| ❌ Toxic    |     -0.16 | retrieved    |            27 | google.adk.tools.base_tool.BaseTool.run_async                                      |

---

### Case: `configure_adk_features_mc:you_are_initializing_an_app_which_parameter_is_mut`
**Query:** You are initializing an `App`. Which parameter is mutually exclusive with providing `app_name` and `root_agent` directly to the `Runner`?

- **Zero-Context Success:** 66.67%
- **Final Max Uncertainty (SE):** 0.1286

| Status      |   Delta P | Source       |   Trials (In) | Document FQN                                                                                         |
|-------------|-----------|--------------|---------------|------------------------------------------------------------------------------------------------------|
| ✅ Critical |      0.26 | random_noise |            29 | vertexai.agent_engines.templates.langchain.LangchainAgent.query                                      |
| yg Helpful  |      0.15 | random_noise |            28 | google.genai.types.RealtimeInputConfig                                                               |
| yg Helpful  |      0.12 | random_noise |            24 | google.adk.agents.base_agent.BaseAgent.canonical_before_agent_callbacks                              |
| yg Helpful  |      0.1  | random_noise |            30 | google.adk.cli.adk_web_server.AdkWebServer.update_session                                            |
| yg Helpful  |      0.09 | retrieved    |            33 | google.adk.cli.cli_tools_click.cli_deploy_cloud_run                                                  |
| yg Helpful  |      0.06 | retrieved    |            24 | google.adk.plugins.base_plugin.BasePlugin.before_run_callback                                        |
| yg Helpful  |      0.06 | retrieved    |            29 | google.adk.agents.agent_config                                                                       |
| ⚪ Noise    |      0.04 | random_noise |            27 | google.adk.models.base_llm.BaseLlm.generate_content_async                                            |
| ⚪ Noise    |      0.02 | random_noise |            28 | vertexai.resources.preview.feature_store.feature_view.FeatureViewSync                                |
| ⚪ Noise    |      0.01 | retrieved    |            31 | google.adk.agents.base_agent.BaseAgent.root_agent                                                    |
| ⚪ Noise    |      0.01 | random_noise |            31 | google.genai.types.DeleteFileSearchStoreConfig                                                       |
| ⚪ Noise    |     -0    | retrieved    |            34 | google.adk.runners.InMemoryRunner                                                                    |
| ⚪ Noise    |     -0    | random_noise |            34 | google.adk.flows.llm_flows.audio_cache_manager                                                       |
| ⚪ Noise    |     -0.03 | retrieved    |            30 | google.adk.agents.run_config                                                                         |
| ⚪ Noise    |     -0.03 | random_noise |            35 | google.genai.types.BatchJob                                                                          |
| ⚪ Noise    |     -0.05 | random_noise |            28 | google.genai.types.LiveClientRealtimeInput                                                           |
| ⚪ Noise    |     -0.06 | retrieved    |            31 | google.adk.runners.Runner.run                                                                        |
| ⚪ Noise    |     -0.06 | random_noise |            31 | google.adk.evaluation.eval_case.EvalCase.ensure_conversation_xor_conversation_scenario               |
| ⚪ Noise    |     -0.07 | retrieved    |            26 | google.adk.agents.invocation_context                                                                 |
| ⚪ Noise    |     -0.07 | random_noise |            29 | google.adk.evaluation.llm_as_judge_utils.get_average_rubric_score                                    |
| ⚪ Noise    |     -0.08 | random_noise |            24 | google.adk.tools.retrieval.vertex_ai_rag_retrieval.VertexAiRagRetrieval                              |
| ⚪ Noise    |     -0.09 | random_noise |            27 | google.adk.code_executors.agent_engine_sandbox_code_executor                                         |
| ⚪ Noise    |     -0.1  | random_noise |            22 | google.adk.artifacts.gcs_artifact_service                                                            |
| ❌ Toxic    |     -0.12 | random_noise |            36 | google.adk.models.lite_llm.LiteLlm.generate_content_async                                            |
| ❌ Toxic    |     -0.12 | random_noise |            36 | google.genai.types.LiveMusicFilteredPromptDict                                                       |
| ❌ Toxic    |     -0.13 | random_noise |            23 | google.adk.memory.in_memory_memory_service.InMemoryMemoryService                                     |
| ❌ Toxic    |     -0.15 | retrieved    |            24 | google.adk.cli.cli_create.run_cmd                                                                    |
| ❌ Toxic    |     -0.16 | retrieved    |            27 | google.adk.cli.cli_deploy.to_cloud_run                                                               |
| ❌ Toxic    |     -0.17 | retrieved    |            30 | google.adk.agents.run_config.RunConfig                                                               |
| ❌ Toxic    |     -0.18 | retrieved    |            25 | google.adk.agents.base_agent_config                                                                  |
| ❌ Toxic    |     -0.18 | random_noise |            28 | vertexai.resources.preview.feature_store.feature_online_store.FeatureOnlineStore.create_feature_view |
| ❌ Toxic    |     -0.2  | random_noise |            20 | google.adk.models.gemini_context_cache_manager.GeminiContextCacheManager.handle_context_caching      |
| ❌ Toxic    |     -0.23 | retrieved    |            30 | google.adk.runners.Runner.run_async                                                                  |
| ❌ Toxic    |     -0.38 | retrieved    |            25 | google.adk.runners.Runner                                                                            |
| ❌ Toxic    |     -0.61 | gold_mined   |            29 | google.adk.apps.app.App                                                                              |

---

### Case: `configure_adk_features_mc:which_google_genai_type_represents_the_fundamental`
**Query:** Which Google GenAI type represents the fundamental unit of content (text, image, function call) within a message?

- **Zero-Context Success:** 66.67%
- **Final Max Uncertainty (SE):** 0.0972

| Status   |   Delta P | Source       |   Trials (In) | Document FQN                                                                               |
|----------|-----------|--------------|---------------|--------------------------------------------------------------------------------------------|
| ⚪ Noise |         0 | retrieved    |            19 | google.genai.types.Content                                                                 |
| ⚪ Noise |         0 | retrieved    |            18 | google.genai.types.ContentDict                                                             |
| ⚪ Noise |         0 | retrieved    |            24 | google.genai.types.Segment                                                                 |
| ⚪ Noise |         0 | retrieved    |            20 | google.genai.types.Document                                                                |
| ⚪ Noise |         0 | retrieved    |            15 | google.genai.types.FunctionResponsePart                                                    |
| ⚪ Noise |         0 | retrieved    |            21 | google.genai.types.FunctionResponseBlob                                                    |
| ⚪ Noise |         0 | retrieved    |            21 | google.genai.types.FunctionResponsePartDict                                                |
| ⚪ Noise |         0 | retrieved    |            29 | google.genai.types.FunctionCall                                                            |
| ⚪ Noise |         0 | retrieved    |            21 | google.genai.types.Blob                                                                    |
| ⚪ Noise |         0 | retrieved    |            19 | google.genai.types.ContentEmbedding                                                        |
| ⚪ Noise |         0 | retrieved    |            23 | google.genai.types.Part.from_function_response                                             |
| ⚪ Noise |         0 | retrieved    |            15 | google.genai.types.FunctionResponseBlobDict                                                |
| ⚪ Noise |         0 | retrieved    |            18 | google.genai.types.SegmentDict                                                             |
| ⚪ Noise |         0 | retrieved    |            22 | google.genai.types.Image                                                                   |
| ⚪ Noise |         0 | retrieved    |            21 | google.genai.types.Part                                                                    |
| ⚪ Noise |         0 | random_noise |            23 | vertexai.preview.rag.utils.resources.KNN                                                   |
| ⚪ Noise |         0 | random_noise |            16 | vertexai.resources.preview.feature_store.feature_online_store.FeatureOnlineStore.delete    |
| ⚪ Noise |         0 | random_noise |            20 | google.genai.tunings.Tunings.cancel                                                        |
| ⚪ Noise |         0 | random_noise |            21 | google.adk.sessions.database_session_service.DynamicPickleType.load_dialect_impl           |
| ⚪ Noise |         0 | random_noise |            17 | google.adk.models.llm_response.LlmResponse.create                                          |
| ⚪ Noise |         0 | random_noise |            18 | google.adk.models.cache_metadata.CacheMetadata                                             |
| ⚪ Noise |         0 | random_noise |            24 | google.adk.evaluation.eval_sets_manager                                                    |
| ⚪ Noise |         0 | random_noise |            21 | google.genai.documents.AsyncDocuments.delete                                               |
| ⚪ Noise |         0 | random_noise |            23 | google.adk.cli.cli_tools_click.HelpfulCommand                                              |
| ⚪ Noise |         0 | random_noise |            19 | google.genai.types.EditImageConfigDict                                                     |
| ⚪ Noise |         0 | random_noise |            20 | google.genai.tunings.Tunings.tune                                                          |
| ⚪ Noise |         0 | random_noise |            17 | vertexai.preview.evaluation.metrics.rubric_based_metric.RubricBasedMetric.generate_rubrics |
| ⚪ Noise |         0 | random_noise |            23 | google.genai.types.PartDict                                                                |
| ⚪ Noise |         0 | random_noise |            22 | google.genai.live.AsyncSession.send_client_content                                         |
| ⚪ Noise |         0 | random_noise |            25 | google.adk.evaluation.llm_as_judge_utils.get_tool_declarations_as_json_str                 |
| ⚪ Noise |         0 | random_noise |            17 | vertexai.resources.preview.feature_store.utils.get_feature_online_store_name               |
| ⚪ Noise |         0 | random_noise |            24 | google.adk.models.anthropic_llm                                                            |
| ⚪ Noise |         0 | random_noise |            18 | google.adk.cli.plugins.recordings_plugin.RecordingsPlugin.before_run_callback              |
| ⚪ Noise |         0 | random_noise |            14 | google.adk.agents.parallel_agent_config.ParallelAgentConfig                                |
| ⚪ Noise |         0 | random_noise |            19 | google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset.OpenAPIToolset.get_tools |

---
