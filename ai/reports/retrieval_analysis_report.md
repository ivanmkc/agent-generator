# Retrieval Dataset Analysis Report

## 1. Executive Summary

- **Total Cases Verified:** 5
- **Total Candidates Analyzed:** 174
- **Average Zero-Context Success Rate:** 46.67%
- **Average Contexts per Trial:** 8.6 documents

This report details the empirical relevance of documentation for each benchmark query, identifying 'Critical' documents (high Delta P) and 'Toxic' distractors.

## 2. Case Breakdown

### Case: `configure_adk_features_mc:which_is_the_correct_import_statement_for_the_runn`
**Query:** Which is the correct import statement for the `Runner` class?

- **Zero-Context Success:** 0.00%
- **Contexts per Trial:** Avg 8.1 (Min: 1, Max: 15)
- **Final Max Uncertainty (SE):** 0.1491

| Status     |   Delta P | Source       |   Trials (In) | Document FQN                                                                               |
|------------|-----------|--------------|---------------|--------------------------------------------------------------------------------------------|
| yg Helpful |      0.18 | retrieved    |            24 | google.adk.runners.Runner.close                                                            |
| yg Helpful |      0.17 | gold_mined   |            21 | google.adk.runners                                                                         |
| yg Helpful |      0.17 | retrieved    |            21 | google.adk.runners.Runner.execute                                                          |
| yg Helpful |      0.17 | retrieved    |            23 | google.adk.runners.Runner.run                                                              |
| yg Helpful |      0.16 | retrieved    |            19 | google.adk.runners.InMemoryRunner                                                          |
| yg Helpful |      0.16 | retrieved    |            18 | google.adk.cli.adk_web_server.AdkWebServer.get_runner_async                                |
| yg Helpful |      0.16 | retrieved    |            16 | google.adk.runners.Runner.run_async                                                        |
| yg Helpful |      0.16 | random_noise |            16 | google.genai.types.SlidingWindowDict                                                       |
| yg Helpful |      0.15 | gold_mined   |            15 | google.adk.runners.Runner                                                                  |
| yg Helpful |      0.12 | random_noise |            25 | vertexai.preview.generative_models.GenerativeModel                                         |
| yg Helpful |      0.12 | random_noise |            24 | google.adk.agents.parallel_agent.ParallelAgent                                             |
| yg Helpful |      0.11 | random_noise |            22 | google.genai.types.GroundingMetadataSourceFlaggingUriDict                                  |
| yg Helpful |      0.1  | retrieved    |            19 | google.adk.a2a.utils.agent_to_a2a.create_runner                                            |
| yg Helpful |      0.08 | random_noise |            16 | google.adk.artifacts.in_memory_artifact_service.InMemoryArtifactService.load_artifact      |
| ⚪ Noise   |      0.04 | retrieved    |            20 | google.adk.plugins.logging_plugin.LoggingPlugin.on_event_callback                          |
| ⚪ Noise   |      0.04 | random_noise |            20 | google.adk.artifacts                                                                       |
| ⚪ Noise   |     -0    | retrieved    |            23 | google.adk.code_executors.base_code_executor                                               |
| ⚪ Noise   |     -0    | random_noise |            23 | google.genai.types.ReplayInteraction                                                       |
| ⚪ Noise   |     -0.02 | retrieved    |            21 | google.adk.agents.run_config.RunConfig                                                     |
| ⚪ Noise   |     -0.02 | random_noise |            21 | google.adk.memory.vertex_ai_rag_memory_service.VertexAiRagMemoryService.search_memory      |
| ⚪ Noise   |     -0.02 | random_noise |            21 | google.genai.pagers                                                                        |
| ⚪ Noise   |     -0.03 | random_noise |            20 | vertexai.resources.preview.feature_store.offline_store.fetch_historical_feature_values     |
| ⚪ Noise   |     -0.03 | random_noise |            20 | google.genai.types.SessionResumptionConfig                                                 |
| ⚪ Noise   |     -0.05 | retrieved    |            18 | google.adk.code_executors.built_in_code_executor                                           |
| ⚪ Noise   |     -0.07 | random_noise |            22 | google.adk.agents.loop_agent.LoopAgentState                                                |
| ⚪ Noise   |     -0.08 | random_noise |            21 | google.adk.cli.adk_web_server.AdkWebServer.internal_lifespan                               |
| ⚪ Noise   |     -0.08 | random_noise |            28 | google.adk.cli.cli_tools_click                                                             |
| ❌ Toxic   |     -0.11 | random_noise |            19 | google.adk.evaluation.local_eval_sets_manager.LocalEvalSetsManager.delete_eval_case        |
| ❌ Toxic   |     -0.11 | random_noise |            24 | google.genai.types.AuthConfigHttpBasicAuthConfig                                           |
| ❌ Toxic   |     -0.13 | random_noise |            17 | google.genai.documents.AsyncDocuments.get                                                  |
| ❌ Toxic   |     -0.14 | random_noise |            27 | google.adk.tools.computer_use.base_computer.BaseComputer.type_text_at                      |
| ❌ Toxic   |     -0.16 | random_noise |            20 | google.adk.evaluation.metric_evaluator_registry.MetricEvaluatorRegistry.register_evaluator |
| ❌ Toxic   |     -0.19 | random_noise |            10 | google.genai.types.DatasetDistribution                                                     |
| ❌ Toxic   |     -0.22 | retrieved    |            20 | google.adk.a2a.converters.request_converter.AgentRunRequest                                |

---

### Case: `configure_adk_features_mc:you_need_to_inspect_an_event_object_which_import_a`
**Query:** You need to inspect an `Event` object. Which import allows you to reference the `Event` class for type hinting?

- **Zero-Context Success:** 100.00%
- **Contexts per Trial:** Avg 9.3 (Min: 2, Max: 16)
- **Final Max Uncertainty (SE):** 0.1447

| Status   |   Delta P | Source       |   Trials (In) | Document FQN                                                                              |
|----------|-----------|--------------|---------------|-------------------------------------------------------------------------------------------|
| ⚪ Noise |         0 | gold_mined   |            14 | google.adk.models                                                                         |
| ⚪ Noise |         0 | gold_mined   |            11 | google.adk.events.event                                                                   |
| ⚪ Noise |         0 | retrieved    |             8 | google.adk.evaluation.eval_case.InvocationEvents                                          |
| ⚪ Noise |         0 | retrieved    |            13 | google.adk.events.event_actions.EventActions                                              |
| ⚪ Noise |         0 | retrieved    |            10 | google.adk.events.event_actions                                                           |
| ⚪ Noise |         0 | retrieved    |            16 | google.adk.events.event.Event                                                             |
| ⚪ Noise |         0 | retrieved    |             9 | google.adk.cli.adk_web_server.GetEventGraphResult                                         |
| ⚪ Noise |         0 | retrieved    |            10 | google.adk.tools.openapi_tool.common.common.TypeHintHelper                                |
| ⚪ Noise |         0 | retrieved    |            12 | google.adk.a2a.converters.event_converter                                                 |
| ⚪ Noise |         0 | retrieved    |            15 | google.adk.sessions.database_session_service.StorageEvent.to_event                        |
| ⚪ Noise |         0 | retrieved    |            17 | google.adk.tools.openapi_tool.common.common.TypeHintHelper.get_type_hint                  |
| ⚪ Noise |         0 | retrieved    |            12 | google.adk.events.event_actions.EventCompaction                                           |
| ⚪ Noise |         0 | retrieved    |             7 | google.adk.cli.adk_web_server.AdkWebServer.event_generator                                |
| ⚪ Noise |         0 | retrieved    |            11 | google.adk.sessions.database_session_service.StorageEvent.from_event                      |
| ⚪ Noise |         0 | retrieved    |            14 | google.adk.evaluation.eval_case.InvocationEvent                                           |
| ⚪ Noise |         0 | retrieved    |            10 | google.adk.tools.openapi_tool.common.common.TypeHintHelper.get_type_value                 |
| ⚪ Noise |         0 | retrieved    |            14 | google.adk.apps.base_events_summarizer.BaseEventsSummarizer                               |
| ⚪ Noise |         0 | random_noise |            19 | google.genai.types.Image.from_file                                                        |
| ⚪ Noise |         0 | random_noise |            12 | google.genai.types.RealtimeInputConfigDict                                                |
| ⚪ Noise |         0 | random_noise |            12 | google.adk.evaluation.in_memory_eval_sets_manager.InMemoryEvalSetsManager.create_eval_set |
| ⚪ Noise |         0 | random_noise |            13 | google.adk.evaluation.eval_metrics.EvalStatus                                             |
| ⚪ Noise |         0 | random_noise |            11 | google.genai.files.Files.upload                                                           |
| ⚪ Noise |         0 | random_noise |            12 | google.genai.types.ListCachedContentsResponse                                             |
| ⚪ Noise |         0 | random_noise |            12 | google.adk.code_executors.container_code_executor.ContainerCodeExecutor                   |
| ⚪ Noise |         0 | random_noise |            10 | google.adk.runners.Runner.run_live                                                        |
| ⚪ Noise |         0 | random_noise |            14 | google.adk.a2a.executor.a2a_agent_executor.A2aAgentExecutorConfig                         |
| ⚪ Noise |         0 | random_noise |            17 | google.adk.models.gemma_llm.Gemma                                                         |
| ⚪ Noise |         0 | random_noise |            14 | google.genai.types.SafetySettingDict                                                      |
| ⚪ Noise |         0 | random_noise |            13 | google.genai.types.LiveMusicSetConfigParametersDict                                       |
| ⚪ Noise |         0 | random_noise |            14 | google.adk.tools.openapi_tool.common.common.PydocHelper.generate_return_doc               |
| ⚪ Noise |         0 | random_noise |            11 | vertexai.agent_engines.templates.adk.AdkApp.async_search_memory                           |
| ⚪ Noise |         0 | random_noise |            14 | google.genai.types.RagRetrievalConfigHybridSearch                                         |
| ⚪ Noise |         0 | random_noise |            15 | google.adk.tools.openapi_tool.auth.auth_helpers                                           |
| ⚪ Noise |         0 | random_noise |            20 | google.genai.types.VideoGenerationMaskDict                                                |
| ⚪ Noise |         0 | random_noise |            16 | google.adk.plugins.base_plugin.BasePlugin.on_event_callback                               |
| ⚪ Noise |         0 | random_noise |             8 | google.genai.types.Model                                                                  |
| ⚪ Noise |         0 | random_noise |            16 | google.genai.types.ActivityStart                                                          |

---

### Case: `configure_adk_features_mc:when_calling_runner_run_async_which_parameter_is_u`
**Query:** When calling `runner.run_async()`, which parameter is used to pass the user's input message?

- **Zero-Context Success:** 0.00%
- **Contexts per Trial:** Avg 8.8 (Min: 3, Max: 18)
- **Final Max Uncertainty (SE):** 0.1458

| Status      |   Delta P | Source       |   Trials (In) | Document FQN                                                                                                                       |
|-------------|-----------|--------------|---------------|------------------------------------------------------------------------------------------------------------------------------------|
| ✅ Critical |      0.82 | retrieved    |            21 | google.adk.runners.Runner.run_async                                                                                                |
| ✅ Critical |      0.43 | retrieved    |            28 | google.adk.runners.Runner.run                                                                                                      |
| ✅ Critical |      0.28 | random_noise |            16 | google.adk.flows.llm_flows.functions.handle_function_calls_live                                                                    |
| ✅ Critical |      0.27 | retrieved    |            18 | google.genai.chats.AsyncChat.send_message                                                                                          |
| ✅ Critical |      0.23 | retrieved    |            23 | google.genai.live.AsyncSession.send                                                                                                |
| yg Helpful  |      0.2  | random_noise |            14 | google.adk.models.base_llm_connection.BaseLlmConnection.send_content                                                               |
| yg Helpful  |      0.09 | retrieved    |            19 | vertexai.agent_engines.templates.adk.AdkApp.async_stream_query                                                                     |
| yg Helpful  |      0.09 | retrieved    |            21 | vertexai.preview.reasoning_engines.templates.adk.AdkApp.async_stream_query                                                         |
| yg Helpful  |      0.09 | random_noise |            21 | google.adk.flows.llm_flows.functions.populate_client_function_call_id                                                              |
| yg Helpful  |      0.09 | random_noise |            19 | google.adk.agents.sequential_agent                                                                                                 |
| yg Helpful  |      0.07 | retrieved    |            15 | google.adk.runners.Runner                                                                                                          |
| ⚪ Noise    |      0.05 | random_noise |            18 | google.genai.live.AsyncSession.send_realtime_input                                                                                 |
| ⚪ Noise    |      0.05 | random_noise |            18 | vertexai.preview.reasoning_engines.templates.langchain.LangchainAgent.clone                                                        |
| ⚪ Noise    |      0.04 | random_noise |            16 | google.genai.types.RetrievalMetadataDict                                                                                           |
| ⚪ Noise    |      0    | random_noise |            22 | google.adk.tools.openapi_tool.auth.credential_exchangers.base_credential_exchanger.BaseAuthCredentialExchanger.exchange_credential |
| ⚪ Noise    |      0    | random_noise |            17 | google.adk.plugins.base_plugin.BasePlugin.after_agent_callback                                                                     |
| ⚪ Noise    |      0    | random_noise |            17 | google.adk.errors                                                                                                                  |
| ⚪ Noise    |     -0.01 | random_noise |            25 | google.genai.operations                                                                                                            |
| ⚪ Noise    |     -0.04 | retrieved    |            26 | google.adk.plugins.base_plugin.BasePlugin.on_user_message_callback                                                                 |
| ⚪ Noise    |     -0.06 | retrieved    |            22 | vertexai.agent_engines.templates.adk.AdkApp.stream_query                                                                           |
| ⚪ Noise    |     -0.07 | random_noise |            17 | vertexai.preview.rag.rag_data.get_file                                                                                             |
| ⚪ Noise    |     -0.07 | random_noise |            17 | vertexai.resources.preview.feature_store.feature_view                                                                              |
| ⚪ Noise    |     -0.1  | random_noise |            21 | vertexai.rag.rag_retrieval                                                                                                         |
| ❌ Toxic    |     -0.11 | random_noise |            24 | google.genai.types.BatchJobSource                                                                                                  |
| ❌ Toxic    |     -0.11 | random_noise |            24 | google.adk.models.gemini_context_cache_manager.GeminiContextCacheManager.handle_context_caching                                    |
| ❌ Toxic    |     -0.12 | retrieved    |            16 | vertexai.preview.reasoning_engines.templates.adk.AdkApp.stream_query                                                               |
| ❌ Toxic    |     -0.15 | retrieved    |            17 | google.adk.tools.base_tool.BaseTool.run_async                                                                                      |
| ❌ Toxic    |     -0.19 | random_noise |            19 | google.adk.tools.google_api_tool.google_api_toolsets.GmailToolset                                                                  |
| ❌ Toxic    |     -0.21 | retrieved    |            20 | google.adk.agents.base_agent.BaseAgent.run_async                                                                                   |
| ❌ Toxic    |     -0.23 | retrieved    |            21 | google.adk.agents.base_agent.BaseAgent._run_async_impl                                                                             |
| ❌ Toxic    |     -0.23 | random_noise |            27 | google.adk.agents.run_config                                                                                                       |
| ❌ Toxic    |     -0.25 | retrieved    |            22 | google.adk.runners.Runner.run_live                                                                                                 |
| ❌ Toxic    |     -0.28 | random_noise |            16 | google.adk.evaluation.rubric_based_evaluator.MeanInvocationResultsSummarizer                                                       |
| ❌ Toxic    |     -0.29 | retrieved    |            12 | google.adk.runners.Runner.run_debug                                                                                                |

---

### Case: `configure_adk_features_mc:you_are_initializing_an_app_which_parameter_is_mut`
**Query:** You are initializing an `App`. Which parameter is mutually exclusive with providing `app_name` and `root_agent` directly to the `Runner`?

- **Zero-Context Success:** 100.00%
- **Contexts per Trial:** Avg 8.2 (Min: 2, Max: 15)
- **Final Max Uncertainty (SE):** 0.1415

| Status      |   Delta P | Source       |   Trials (In) | Document FQN                                                                                                                       |
|-------------|-----------|--------------|---------------|------------------------------------------------------------------------------------------------------------------------------------|
| ✅ Critical |      0.27 | random_noise |            10 | google.adk.sessions.sqlite_session_service.SqliteSessionService.list_sessions                                                      |
| ✅ Critical |      0.25 | retrieved    |            19 | google.adk.agents.run_config.RunConfig                                                                                             |
| ✅ Critical |      0.25 | random_noise |            19 | google.genai.caches.AsyncCaches.update                                                                                             |
| yg Helpful  |      0.15 | random_noise |            17 | google.genai.types.ReplayInteractionDict                                                                                           |
| yg Helpful  |      0.13 | retrieved    |            21 | google.adk.cli.cli_tools_click.cli_deploy_cloud_run                                                                                |
| yg Helpful  |      0.13 | retrieved    |            15 | google.adk.agents.invocation_context                                                                                               |
| yg Helpful  |      0.12 | random_noise |            14 | vertexai.resources.preview.feature_store.utils.AlgorithmConfig                                                                     |
| yg Helpful  |      0.11 | random_noise |            25 | google.genai.types.ComputerUseDict                                                                                                 |
| yg Helpful  |      0.1  | retrieved    |            13 | google.adk.runners.Runner.run_async                                                                                                |
| yg Helpful  |      0.06 | random_noise |            21 | google.adk.evaluation.metric_evaluator_registry.MetricEvaluatorRegistry.get_evaluator                                              |
| ⚪ Noise    |      0.05 | retrieved    |            15 | google.adk.runners.InMemoryRunner                                                                                                  |
| ⚪ Noise    |      0.04 | retrieved    |            24 | google.adk.agents.agent_config                                                                                                     |
| ⚪ Noise    |      0.04 | random_noise |            19 | google.adk.cli.built_in_agents.sub_agents.url_context_agent.create_url_context_agent                                               |
| ⚪ Noise    |      0.04 | random_noise |            24 | google.genai.types.Schema.copy_schema_fields                                                                                       |
| ⚪ Noise    |      0.04 | random_noise |            19 | google.adk.cli.built_in_agents.tools.write_files                                                                                   |
| ⚪ Noise    |      0.03 | retrieved    |            14 | google.adk.cli.cli_create.run_cmd                                                                                                  |
| ⚪ Noise    |      0.02 | random_noise |            18 | google.genai.types.GroundingSupport                                                                                                |
| ⚪ Noise    |      0.02 | random_noise |            18 | vertexai.preview.rag.rag_retrieval                                                                                                 |
| ⚪ Noise    |      0.01 | retrieved    |            22 | google.adk.cli.cli_deploy.to_cloud_run                                                                                             |
| ⚪ Noise    |      0    | retrieved    |            17 | google.adk.agents.base_agent_config                                                                                                |
| ⚪ Noise    |      0    | random_noise |            17 | google.adk.tools.openapi_tool.auth.credential_exchangers.base_credential_exchanger.BaseAuthCredentialExchanger.exchange_credential |
| ⚪ Noise    |     -0.03 | random_noise |            23 | google.adk.apps.app.EventsCompactionConfig                                                                                         |
| ⚪ Noise    |     -0.03 | random_noise |            23 | google.adk.events.event_actions                                                                                                    |
| ⚪ Noise    |     -0.05 | random_noise |            18 | google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session                                                   |
| ⚪ Noise    |     -0.09 | random_noise |            20 | google.genai.types.TunedModelInfo                                                                                                  |
| ❌ Toxic    |     -0.11 | retrieved    |            19 | google.adk.runners.Runner.run                                                                                                      |
| ❌ Toxic    |     -0.15 | retrieved    |            17 | google.adk.plugins.base_plugin.BasePlugin.before_run_callback                                                                      |
| ❌ Toxic    |     -0.15 | retrieved    |            20 | google.adk.agents.base_agent.BaseAgent.root_agent                                                                                  |
| ❌ Toxic    |     -0.23 | retrieved    |            17 | google.adk.agents.run_config                                                                                                       |
| ❌ Toxic    |     -0.23 | random_noise |            17 | google.adk.artifacts.in_memory_artifact_service.InMemoryArtifactService.load_artifact                                              |
| ❌ Toxic    |     -0.24 | random_noise |            14 | google.genai.types.LiveConnectConfigDict                                                                                           |
| ❌ Toxic    |     -0.25 | random_noise |            19 | vertexai.rag.rag_store                                                                                                             |
| ❌ Toxic    |     -0.38 | retrieved    |            24 | google.adk.runners.Runner                                                                                                          |
| ❌ Toxic    |     -0.59 | gold_mined   |            14 | google.adk.apps.app.App                                                                                                            |

---

### Case: `configure_adk_features_mc:which_google_genai_type_represents_the_fundamental`
**Query:** Which Google GenAI type represents the fundamental unit of content (text, image, function call) within a message?

- **Zero-Context Success:** 33.33%
- **Contexts per Trial:** Avg 9.0 (Min: 4, Max: 15)
- **Final Max Uncertainty (SE):** 0.1403

| Status      |   Delta P | Source       |   Trials (In) | Document FQN                                                                                         |
|-------------|-----------|--------------|---------------|------------------------------------------------------------------------------------------------------|
| ✅ Critical |      0.38 | retrieved    |            18 | google.genai.types.Part                                                                              |
| ✅ Critical |      0.3  | retrieved    |            18 | google.genai.types.Document                                                                          |
| ✅ Critical |      0.29 | retrieved    |            17 | google.genai.types.ContentDict                                                                       |
| ✅ Critical |      0.29 | retrieved    |            17 | google.genai.types.Part.from_function_response                                                       |
| ✅ Critical |      0.25 | retrieved    |            20 | google.genai.types.FunctionResponsePart                                                              |
| ✅ Critical |      0.22 | retrieved    |            23 | google.genai.types.Content                                                                           |
| ✅ Critical |      0.22 | random_noise |            17 | google.adk.tools.enterprise_search_tool.EnterpriseWebSearchTool                                      |
| yg Helpful  |      0.2  | retrieved    |            21 | google.genai.types.ContentEmbedding                                                                  |
| yg Helpful  |      0.14 | random_noise |            17 | vertexai.preview.evaluation.metrics.pairwise_metric.PairwiseMetric                                   |
| yg Helpful  |      0.14 | random_noise |            12 | google.genai.types.ProductImageDict                                                                  |
| yg Helpful  |      0.13 | random_noise |            21 | google.genai.types.DownloadFileConfigDict                                                            |
| yg Helpful  |      0.12 | random_noise |            16 | google.adk.tools.bigquery.metadata_tool.list_dataset_ids                                             |
| yg Helpful  |      0.1  | retrieved    |            27 | google.genai.types.Blob                                                                              |
| yg Helpful  |      0.1  | random_noise |            23 | google.genai.types.LiveClientContent                                                                 |
| yg Helpful  |      0.09 | retrieved    |            14 | google.genai.types.FunctionResponsePartDict                                                          |
| yg Helpful  |      0.08 | retrieved    |            18 | google.genai.types.FunctionCall                                                                      |
| yg Helpful  |      0.08 | retrieved    |            22 | google.genai.types.Image                                                                             |
| yg Helpful  |      0.06 | retrieved    |            17 | google.genai.types.Segment                                                                           |
| yg Helpful  |      0.06 | random_noise |            17 | google.genai.caches.Caches                                                                           |
| yg Helpful  |      0.06 | random_noise |            21 | google.adk.auth                                                                                      |
| ⚪ Noise    |      0.04 | random_noise |            31 | google.genai.types.SupervisedTuningSpecDict                                                          |
| ⚪ Noise    |      0.03 | random_noise |            19 | google.adk.plugins.bigquery_agent_analytics_plugin.BigQueryAgentAnalyticsPlugin.before_tool_callback |
| ⚪ Noise    |      0.02 | random_noise |            15 | google.adk.tools.url_context_tool                                                                    |
| ⚪ Noise    |      0.02 | random_noise |            15 | google.adk.cli.adk_web_server.AddSessionToEvalSetRequest                                             |
| ⚪ Noise    |     -0.03 | random_noise |            23 | google.adk.sessions.database_session_service.set_sqlite_pragma                                       |
| ⚪ Noise    |     -0.03 | random_noise |            13 | google.adk.evaluation.conversation_scenarios.ConversationScenario                                    |
| ⚪ Noise    |     -0.04 | random_noise |            16 | google.genai.types.GroundingChunkRetrievedContextDict                                                |
| ⚪ Noise    |     -0.05 | retrieved    |            22 | google.genai.types.FunctionResponseBlob                                                              |
| ⚪ Noise    |     -0.05 | random_noise |            22 | google.adk.cli.adk_web_server.AdkWebServer.run_agent_sse                                             |
| ⚪ Noise    |     -0.07 | random_noise |            18 | google.genai.types.FunctionResponseDict                                                              |
| ⚪ Noise    |     -0.09 | retrieved    |            14 | google.genai.types.FunctionResponseBlobDict                                                          |
| ⚪ Noise    |     -0.09 | random_noise |            20 | google.adk.sessions.state.State.update                                                               |
| ❌ Toxic    |     -0.14 | retrieved    |            21 | google.genai.types.SegmentDict                                                                       |
| ❌ Toxic    |     -0.14 | random_noise |            18 | vertexai.resources.preview.feature_store.feature_group.FeatureGroup.get_feature_monitor              |
| ❌ Toxic    |     -0.24 | random_noise |            22 | vertexai.agent_engines.templates.adk.AdkApp.create_session                                           |

---
