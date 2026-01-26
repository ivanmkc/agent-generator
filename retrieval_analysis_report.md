# Retrieval Dataset Analysis Report

## 1. Executive Summary

- **Total Cases Verified:** 5
- **Total Candidates Analyzed:** 176
- **Average Zero-Context Success Rate:** 33.33%

This report details the empirical relevance of documentation for each benchmark query, identifying 'Critical' documents (high Delta P) and 'Toxic' distractors.

## 2. Case Breakdown

### Case: `configure_adk_features_mc:which_is_the_correct_import_statement_for_the_runn`
**Query:** Which is the correct import statement for the `Runner` class?

- **Zero-Context Success:** 0.00%
- **Final Max Uncertainty (SE):** 0.0932

| Status   |   Delta P | Source       |   Trials (In) | Document FQN                                                                               |
|----------|-----------|--------------|---------------|--------------------------------------------------------------------------------------------|
| ⚪ Noise |         0 | gold_mined   |            22 | google.adk.runners                                                                         |
| ⚪ Noise |         0 | gold_mined   |            20 | google.adk.runners.Runner                                                                  |
| ⚪ Noise |         0 | retrieved    |            16 | google.adk.runners.Runner.execute                                                          |
| ⚪ Noise |         0 | retrieved    |            19 | google.adk.runners.Runner.close                                                            |
| ⚪ Noise |         0 | retrieved    |            15 | google.adk.runners.InMemoryRunner                                                          |
| ⚪ Noise |         0 | retrieved    |            21 | google.adk.a2a.utils.agent_to_a2a.create_runner                                            |
| ⚪ Noise |         0 | retrieved    |            20 | google.adk.runners.Runner.run                                                              |
| ⚪ Noise |         0 | retrieved    |            19 | google.adk.cli.adk_web_server.AdkWebServer.get_runner_async                                |
| ⚪ Noise |         0 | retrieved    |            24 | google.adk.agents.run_config.RunConfig                                                     |
| ⚪ Noise |         0 | retrieved    |            14 | google.adk.code_executors.built_in_code_executor                                           |
| ⚪ Noise |         0 | retrieved    |            24 | google.adk.runners.Runner.run_async                                                        |
| ⚪ Noise |         0 | retrieved    |            18 | google.adk.code_executors.base_code_executor                                               |
| ⚪ Noise |         0 | retrieved    |            20 | google.adk.plugins.logging_plugin.LoggingPlugin.on_event_callback                          |
| ⚪ Noise |         0 | retrieved    |            17 | google.adk.a2a.converters.request_converter.AgentRunRequest                                |
| ⚪ Noise |         0 | random_noise |            16 | google.adk.artifacts.in_memory_artifact_service.InMemoryArtifactService.list_versions      |
| ⚪ Noise |         0 | random_noise |            21 | google.adk.cli.adk_web_server.AdkWebServer.process_messages                                |
| ⚪ Noise |         0 | random_noise |            17 | google.genai.tunings.AsyncTunings                                                          |
| ⚪ Noise |         0 | random_noise |            16 | google.adk.artifacts.file_artifact_service.FileArtifactService.list_artifact_versions      |
| ⚪ Noise |         0 | random_noise |            17 | google.genai.types.GeminiPreferenceExampleCompletionDict                                   |
| ⚪ Noise |         0 | random_noise |            14 | google.genai.types.HttpRetryOptions                                                        |
| ⚪ Noise |         0 | random_noise |            19 | google.adk.agents.invocation_context.RealtimeCacheEntry                                    |
| ⚪ Noise |         0 | random_noise |            17 | google.adk.evaluation.app_details.AppDetails                                               |
| ⚪ Noise |         0 | random_noise |            17 | google.adk.plugins.reflect_retry_tool_plugin.ReflectAndRetryToolPlugin.after_tool_callback |
| ⚪ Noise |         0 | random_noise |            14 | google.adk.cli.service_registry.agentengine_session_factory                                |
| ⚪ Noise |         0 | random_noise |            21 | google.genai.types.GroundingChunkDict                                                      |
| ⚪ Noise |         0 | random_noise |            21 | google.adk.tools.computer_use.computer_use_toolset.ComputerUseToolset.get_tools            |
| ⚪ Noise |         0 | random_noise |            19 | google.adk.plugins.logging_plugin.LoggingPlugin.before_model_callback                      |
| ⚪ Noise |         0 | random_noise |            12 | vertexai.preview.rag.rag_data.get_rag_engine_config                                        |
| ⚪ Noise |         0 | random_noise |            20 | google.genai.caches.AsyncCaches.list                                                       |
| ⚪ Noise |         0 | random_noise |            19 | google.genai.types.Scale                                                                   |
| ⚪ Noise |         0 | random_noise |            21 | google.adk.flows.llm_flows.audio_transcriber                                               |
| ⚪ Noise |         0 | random_noise |            18 | vertexai.preview.evaluation.utils.parse_question                                           |
| ⚪ Noise |         0 | random_noise |            22 | google.adk.planners.built_in_planner.BuiltInPlanner.build_planning_instruction             |
| ⚪ Noise |         0 | random_noise |            21 | google.adk.tools.openapi_tool.common                                                       |

---

### Case: `configure_adk_features_mc:you_need_to_inspect_an_event_object_which_import_a`
**Query:** You need to inspect an `Event` object. Which import allows you to reference the `Event` class for type hinting?

- **Zero-Context Success:** 100.00%
- **Final Max Uncertainty (SE):** 0.0970

| Status     |   Delta P | Source       |   Trials (In) | Document FQN                                                                          |
|------------|-----------|--------------|---------------|---------------------------------------------------------------------------------------|
| yg Helpful |      0.08 | retrieved    |            22 | google.adk.tools.openapi_tool.common.common.TypeHintHelper.get_type_hint              |
| yg Helpful |      0.07 | retrieved    |            19 | google.adk.tools.openapi_tool.common.common.TypeHintHelper.get_type_value             |
| yg Helpful |      0.07 | random_noise |            19 | google.adk.models.gemini_context_cache_manager.GeminiContextCacheManager              |
| yg Helpful |      0.07 | random_noise |            19 | google.genai.types.CachedContentUsageMetadata                                         |
| yg Helpful |      0.07 | random_noise |            20 | google.adk.code_executors.code_executor_context.CodeExecutorContext.clear_input_files |
| yg Helpful |      0.07 | random_noise |            19 | google.adk.evaluation.eval_metrics                                                    |
| yg Helpful |      0.07 | random_noise |            19 | google.adk.sessions.database_session_service.StorageEvent.long_running_tool_ids       |
| yg Helpful |      0.07 | random_noise |            19 | google.adk.a2a.utils.agent_to_a2a.setup_a2a                                           |
| yg Helpful |      0.06 | gold_mined   |            16 | google.adk.events.event                                                               |
| yg Helpful |      0.06 | retrieved    |            17 | google.adk.cli.adk_web_server.GetEventGraphResult                                     |
| yg Helpful |      0.06 | retrieved    |            18 | google.adk.sessions.database_session_service.StorageEvent.to_event                    |
| yg Helpful |      0.06 | retrieved    |            18 | google.adk.events.event_actions.EventCompaction                                       |
| yg Helpful |      0.06 | retrieved    |            17 | google.adk.cli.adk_web_server.AdkWebServer.event_generator                            |
| yg Helpful |      0.06 | retrieved    |            17 | google.adk.apps.base_events_summarizer.BaseEventsSummarizer                           |
| yg Helpful |      0.06 | random_noise |            16 | google.adk.auth.auth_credential.HttpCredentials.model_validate                        |
| yg Helpful |      0.06 | random_noise |            18 | google.adk.tools.toolbox_toolset                                                      |
| yg Helpful |      0.06 | random_noise |            18 | google.adk.models.anthropic_llm.part_to_message_block                                 |
| yg Helpful |      0.06 | random_noise |            18 | google.adk.evaluation.metric_evaluator_registry.MetricEvaluatorRegistry               |
| ⚪ Noise   |      0.05 | retrieved    |            14 | google.adk.tools.openapi_tool.common.common.TypeHintHelper                            |
| ⚪ Noise   |      0.05 | retrieved    |            14 | google.adk.sessions.database_session_service.StorageEvent.from_event                  |
| ⚪ Noise   |      0.05 | random_noise |            15 | vertexai.preview.reasoning_engines.templates.adk                                      |
| ⚪ Noise   |      0.05 | random_noise |            14 | google.adk.plugins.bigquery_agent_analytics_plugin.to_arrow_schema                    |
| ⚪ Noise   |     -0.05 | retrieved    |            21 | google.adk.a2a.converters.event_converter                                             |
| ⚪ Noise   |     -0.05 | retrieved    |            20 | google.adk.evaluation.eval_case.InvocationEvent                                       |
| ⚪ Noise   |     -0.05 | random_noise |            19 | google.adk.cli.conformance.adk_web_server_client.AdkWebServerClient                   |
| ⚪ Noise   |     -0.05 | random_noise |            19 | vertexai.preview.extensions                                                           |
| ⚪ Noise   |     -0.05 | random_noise |            22 | vertexai.agent_engines.templates.langgraph.LanggraphAgent.get_state_history           |
| ⚪ Noise   |     -0.05 | random_noise |            20 | google.genai.types.AuthConfig                                                         |
| ⚪ Noise   |     -0.05 | random_noise |            20 | google.genai.models.Models.generate_videos                                            |
| ⚪ Noise   |     -0.06 | gold_mined   |            17 | google.adk.models                                                                     |
| ⚪ Noise   |     -0.06 | retrieved    |            17 | google.adk.evaluation.eval_case.InvocationEvents                                      |
| ⚪ Noise   |     -0.06 | retrieved    |            18 | google.adk.events.event.Event                                                         |
| ⚪ Noise   |     -0.07 | retrieved    |            14 | google.adk.events.event_actions.EventActions                                          |
| ⚪ Noise   |     -0.07 | random_noise |            15 | vertexai.rag.utils.resources.Basic                                                    |
| ⚪ Noise   |     -0.07 | random_noise |            14 | google.adk.tools.apihub_tool.clients.apihub_client.APIHubClient.get_api               |
| ⚪ Noise   |     -0.09 | retrieved    |            11 | google.adk.events.event_actions                                                       |
| ⚪ Noise   |     -0.09 | random_noise |            11 | google.adk.plugins.plugin_manager.PluginManager.run_on_user_message_callback          |

---

### Case: `configure_adk_features_mc:when_calling_runner_run_async_which_parameter_is_u`
**Query:** When calling `runner.run_async()`, which parameter is used to pass the user's input message?

- **Zero-Context Success:** 0.00%
- **Final Max Uncertainty (SE):** 0.1763

| Status      |   Delta P | Source       |   Trials (In) | Document FQN                                                                                                                       |
|-------------|-----------|--------------|---------------|------------------------------------------------------------------------------------------------------------------------------------|
| ✅ Critical |      0.81 | retrieved    |            13 | google.adk.runners.Runner.run_async                                                                                                |
| ✅ Critical |      0.36 | random_noise |            21 | google.adk.tools.openapi_tool.auth.credential_exchangers.base_credential_exchanger.BaseAuthCredentialExchanger.exchange_credential |
| ✅ Critical |      0.3  | retrieved    |            20 | google.adk.runners.Runner.run                                                                                                      |
| ✅ Critical |      0.3  | random_noise |            20 | google.genai.types.DeleteFileSearchStoreConfigDict                                                                                 |
| ✅ Critical |      0.29 | retrieved    |            25 | google.adk.runners.Runner                                                                                                          |
| ✅ Critical |      0.26 | retrieved    |            21 | google.genai.live.AsyncSession.send                                                                                                |
| ✅ Critical |      0.21 | random_noise |            22 | google.adk.evaluation.in_memory_eval_sets_manager.InMemoryEvalSetsManager.add_eval_case                                            |
| yg Helpful  |      0.19 | random_noise |            16 | vertexai.preview.reasoning_engines.templates.ag2.AG2Agent.clone                                                                    |
| yg Helpful  |      0.19 | random_noise |            18 | google.adk.agents.loop_agent.LoopAgentState                                                                                        |
| yg Helpful  |      0.17 | retrieved    |            23 | vertexai.agent_engines.templates.adk.AdkApp.stream_query                                                                           |
| yg Helpful  |      0.15 | retrieved    |            19 | vertexai.preview.reasoning_engines.templates.adk.AdkApp.async_stream_query                                                         |
| yg Helpful  |      0.12 | random_noise |            24 | google.genai.chats.Chat                                                                                                            |
| yg Helpful  |      0.1  | retrieved    |            20 | google.adk.plugins.base_plugin.BasePlugin.on_user_message_callback                                                                 |
| yg Helpful  |      0.1  | random_noise |            20 | vertexai.preview.example_stores                                                                                                    |
| yg Helpful  |      0.1  | random_noise |            20 | google.genai.types.CandidateDict                                                                                                   |
| ⚪ Noise    |      0.02 | random_noise |            24 | google.genai.types.BatchJobSourceDict                                                                                              |
| ⚪ Noise    |      0.01 | retrieved    |            22 | vertexai.agent_engines.templates.adk.AdkApp.async_stream_query                                                                     |
| ⚪ Noise    |      0.01 | random_noise |            22 | vertexai.preview.reasoning_engines.templates.adk.AdkApp.set_up                                                                     |
| ⚪ Noise    |      0    | retrieved    |            20 | google.adk.agents.base_agent.BaseAgent._run_async_impl                                                                             |
| ⚪ Noise    |      0    | random_noise |            20 | google.genai.types.LiveMusicSetConfigParametersDict                                                                                |
| ⚪ Noise    |     -0.01 | retrieved    |            29 | google.adk.runners.Runner.run_live                                                                                                 |
| ⚪ Noise    |     -0.02 | random_noise |            16 | google.genai.types.GenerateImagesResponse.images                                                                                   |
| ⚪ Noise    |     -0.04 | retrieved    |            23 | google.adk.runners.Runner.run_debug                                                                                                |
| ⚪ Noise    |     -0.06 | random_noise |            19 | google.genai.types.Language                                                                                                        |
| ⚪ Noise    |     -0.1  | random_noise |            20 | vertexai.agent_engines.templates.adk.AdkApp.clone                                                                                  |
| ⚪ Noise    |     -0.1  | random_noise |            20 | google.adk.evaluation.llm_as_judge_utils.Label                                                                                     |
| ❌ Toxic    |     -0.11 | retrieved    |            18 | google.genai.chats.AsyncChat.send_message                                                                                          |
| ❌ Toxic    |     -0.12 | random_noise |            16 | google.genai.types.LiveServerGoAwayDict                                                                                            |
| ❌ Toxic    |     -0.13 | random_noise |            25 | google.adk.evaluation.eval_result.EvalCaseResult                                                                                   |
| ❌ Toxic    |     -0.14 | retrieved    |            23 | vertexai.preview.reasoning_engines.templates.adk.AdkApp.stream_query                                                               |
| ❌ Toxic    |     -0.14 | random_noise |            23 | vertexai.resources.preview.ml_monitoring.spec.schema                                                                               |
| ❌ Toxic    |     -0.15 | retrieved    |            21 | google.adk.tools.base_tool.BaseTool.run_async                                                                                      |
| ❌ Toxic    |     -0.19 | random_noise |            24 | google.adk.cli.utils.agent_loader.AgentLoader.load_agent                                                                           |
| ❌ Toxic    |     -0.31 | retrieved    |            18 | google.adk.agents.base_agent.BaseAgent.run_async                                                                                   |
| ❌ Toxic    |     -0.4  | random_noise |            20 | google.genai.types.ModalityTokenCount                                                                                              |

---

### Case: `configure_adk_features_mc:you_are_initializing_an_app_which_parameter_is_mut`
**Query:** You are initializing an `App`. Which parameter is mutually exclusive with providing `app_name` and `root_agent` directly to the `Runner`?

- **Zero-Context Success:** 66.67%
- **Final Max Uncertainty (SE):** 0.1524

| Status      |   Delta P | Source       |   Trials (In) | Document FQN                                                                               |
|-------------|-----------|--------------|---------------|--------------------------------------------------------------------------------------------|
| ✅ Critical |      0.22 | random_noise |            21 | vertexai.preview.evaluation.notebook_utils.display_eval_result                             |
| yg Helpful  |      0.2  | retrieved    |            22 | google.adk.cli.cli_tools_click.cli_deploy_cloud_run                                        |
| yg Helpful  |      0.18 | random_noise |            19 | google.adk.cli.service_registry.ServiceRegistry.create_session_service                     |
| yg Helpful  |      0.17 | random_noise |            23 | google.genai.types.DynamicRetrievalConfig                                                  |
| yg Helpful  |      0.17 | random_noise |            16 | vertexai.preview.reasoning_engines.templates.adk.AdkApp.async_create_session               |
| yg Helpful  |      0.17 | random_noise |            23 | google.adk.tools.google_api_tool.google_api_toolsets.GmailToolset                          |
| yg Helpful  |      0.15 | retrieved    |            20 | google.adk.plugins.base_plugin.BasePlugin.before_run_callback                              |
| yg Helpful  |      0.14 | random_noise |            17 | google.genai.types.GetCachedContentConfig                                                  |
| yg Helpful  |      0.12 | random_noise |            21 | vertexai.rag.utils.resources.RagVectorDbConfig                                             |
| yg Helpful  |      0.12 | random_noise |            21 | google.adk.code_executors.unsafe_local_code_executor.UnsafeLocalCodeExecutor.execute_code  |
| yg Helpful  |      0.11 | retrieved    |            18 | google.adk.agents.invocation_context                                                       |
| yg Helpful  |      0.1  | random_noise |            22 | vertexai.resources.preview.feature_store.feature_group.FeatureGroup.create_feature_monitor |
| yg Helpful  |      0.09 | random_noise |            26 | google.adk.cli.fast_api.register_processors                                                |
| yg Helpful  |      0.08 | retrieved    |            19 | google.adk.agents.run_config.RunConfig                                                     |
| yg Helpful  |      0.06 | random_noise |            16 | google.genai.types.GroundingSupportDict                                                    |
| ⚪ Noise    |      0.02 | random_noise |            21 | google.adk.utils.model_name_utils                                                          |
| ⚪ Noise    |      0.01 | random_noise |            18 | google.adk.models.lite_llm.UsageMetadataChunk                                              |
| ⚪ Noise    |     -0.02 | retrieved    |            19 | google.adk.agents.base_agent.BaseAgent.root_agent                                          |
| ⚪ Noise    |     -0.04 | random_noise |            16 | vertexai.evaluation.eval_task.EvalTask.evaluate                                            |
| ⚪ Noise    |     -0.05 | retrieved    |            20 | google.adk.agents.base_agent_config                                                        |
| ⚪ Noise    |     -0.05 | retrieved    |            20 | google.adk.agents.run_config                                                               |
| ⚪ Noise    |     -0.07 | retrieved    |            17 | google.adk.cli.cli_deploy.to_cloud_run                                                     |
| ⚪ Noise    |     -0.07 | random_noise |            17 | google.adk.events.event.Event.get_function_calls                                           |
| ⚪ Noise    |     -0.08 | retrieved    |            21 | google.adk.agents.agent_config                                                             |
| ⚪ Noise    |     -0.08 | random_noise |            21 | google.adk.evaluation.local_eval_sets_manager.LocalEvalSetsManager.get_eval_case           |
| ⚪ Noise    |     -0.08 | random_noise |            21 | google.genai.operations.AsyncOperations.get                                                |
| ⚪ Noise    |     -0.09 | retrieved    |            25 | google.adk.runners.Runner.run_async                                                        |
| ⚪ Noise    |     -0.1  | random_noise |            18 | google.adk.planners.base_planner.BasePlanner.build_planning_instruction                    |
| ❌ Toxic    |     -0.13 | retrieved    |            26 | google.adk.runners.InMemoryRunner                                                          |
| ❌ Toxic    |     -0.18 | random_noise |            21 | google.adk.sessions.database_session_service.DynamicPickleType                             |
| ❌ Toxic    |     -0.23 | retrieved    |            15 | google.adk.runners.Runner.run                                                              |
| ❌ Toxic    |     -0.31 | random_noise |            25 | google.adk.tools.retrieval                                                                 |
| ❌ Toxic    |     -0.32 | retrieved    |            19 | google.adk.cli.cli_create.run_cmd                                                          |
| ❌ Toxic    |     -0.42 | retrieved    |            19 | google.adk.runners.Runner                                                                  |
| ❌ Toxic    |     -0.45 | gold_mined   |            20 | google.adk.apps.app.App                                                                    |

---

### Case: `configure_adk_features_mc:which_google_genai_type_represents_the_fundamental`
**Query:** Which Google GenAI type represents the fundamental unit of content (text, image, function call) within a message?

- **Zero-Context Success:** 0.00%
- **Final Max Uncertainty (SE):** 0.0984

| Status     |   Delta P | Source       |   Trials (In) | Document FQN                                                                                                        |
|------------|-----------|--------------|---------------|---------------------------------------------------------------------------------------------------------------------|
| yg Helpful |      0.07 | random_noise |            22 | google.genai.types.TokensInfo                                                                                       |
| yg Helpful |      0.06 | retrieved    |            20 | google.genai.types.FunctionResponseBlob                                                                             |
| yg Helpful |      0.06 | retrieved    |            20 | google.genai.types.FunctionResponsePartDict                                                                         |
| yg Helpful |      0.06 | retrieved    |            19 | google.genai.types.Part                                                                                             |
| yg Helpful |      0.06 | random_noise |            20 | google.adk.cli.agent_graph.should_build_agent_cluster                                                               |
| yg Helpful |      0.06 | random_noise |            20 | google.adk.plugins.bigquery_agent_analytics_plugin.BigQueryAgentAnalyticsPlugin.before_tool_callback                |
| yg Helpful |      0.06 | random_noise |            19 | google.adk.evaluation.eval_set_results_manager                                                                      |
| ⚪ Noise   |      0.05 | retrieved    |            16 | google.genai.types.Document                                                                                         |
| ⚪ Noise   |      0.05 | retrieved    |            17 | google.genai.types.ContentEmbedding                                                                                 |
| ⚪ Noise   |      0.05 | retrieved    |            15 | google.genai.types.SegmentDict                                                                                      |
| ⚪ Noise   |      0.05 | random_noise |            16 | vertexai.resources.preview.ml_monitoring.model_monitors.AlertsSearchResponse.raw_search_alerts_response             |
| ⚪ Noise   |      0.05 | random_noise |            16 | google.adk.utils.model_name_utils.is_gemini_1_model                                                                 |
| ⚪ Noise   |      0.05 | random_noise |            18 | google.adk.cli.utils.local_storage                                                                                  |
| ⚪ Noise   |      0.05 | random_noise |            18 | google.adk.cli.adk_web_server.ListMetricsInfoResponse                                                               |
| ⚪ Noise   |      0.05 | random_noise |            17 | google.genai.types.FileDict                                                                                         |
| ⚪ Noise   |      0.05 | random_noise |            17 | google.genai.types.GeneratedImageDict                                                                               |
| ⚪ Noise   |      0.05 | random_noise |            18 | google.adk.tools.application_integration_tool.clients.connections_client.ConnectionsClient.list_operation           |
| ⚪ Noise   |      0.04 | retrieved    |            14 | google.genai.types.FunctionResponsePart                                                                             |
| ⚪ Noise   |      0.04 | retrieved    |            14 | google.genai.types.Part.from_function_response                                                                      |
| ⚪ Noise   |     -0.04 | retrieved    |            23 | google.genai.types.Content                                                                                          |
| ⚪ Noise   |     -0.04 | random_noise |            26 | google.adk.tools.openapi_tool.auth.credential_exchangers.auto_auth_credential_exchanger.AutoAuthCredentialExchanger |
| ⚪ Noise   |     -0.05 | retrieved    |            21 | google.genai.types.ContentDict                                                                                      |
| ⚪ Noise   |     -0.05 | retrieved    |            20 | google.genai.types.Segment                                                                                          |
| ⚪ Noise   |     -0.05 | retrieved    |            20 | google.genai.types.FunctionCall                                                                                     |
| ⚪ Noise   |     -0.05 | retrieved    |            20 | google.genai.types.Blob                                                                                             |
| ⚪ Noise   |     -0.05 | random_noise |            19 | vertexai.preview.reasoning_engines.templates.langchain.LangchainAgent.set_up                                        |
| ⚪ Noise   |     -0.05 | random_noise |            20 | google.adk.cli.adk_web_server.GetEventGraphResult                                                                   |
| ⚪ Noise   |     -0.05 | random_noise |            19 | google.genai.types.Language                                                                                         |
| ⚪ Noise   |     -0.06 | retrieved    |            18 | google.genai.types.FunctionResponseBlobDict                                                                         |
| ⚪ Noise   |     -0.06 | retrieved    |            17 | google.genai.types.Image                                                                                            |
| ⚪ Noise   |     -0.06 | random_noise |            18 | vertexai.preview.reasoning_engines.templates.ag2.AG2Agent                                                           |
| ⚪ Noise   |     -0.06 | random_noise |            17 | google.adk.agents.callback_context.CallbackContext.load_artifact                                                    |
| ⚪ Noise   |     -0.06 | random_noise |            17 | google.genai.types.DeleteFileResponse                                                                               |
| ⚪ Noise   |     -0.06 | random_noise |            16 | vertexai.agent_engines.templates.langgraph.LanggraphAgent.register_operations                                       |
| ⚪ Noise   |     -0.06 | random_noise |            18 | google.genai.types.GroundingChunkWebDict                                                                            |

---
