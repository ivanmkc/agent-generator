# Retrieval Dataset Analysis Report

## 1. Executive Summary

- **Total Cases Verified:** 2
- **Total Candidates Analyzed:** 71
- **Average Zero-Context Success Rate:** 50.00%
- **Average Contexts per Trial:** 8.7 documents

This report details the empirical relevance of documentation for each benchmark query, identifying 'Critical' documents (high Delta P) and 'Toxic' distractors.

## 2. Case Breakdown

### Case: `configure_adk_features_mc:which_is_the_correct_import_statement_for_the_runn`
**Query:** Which is the correct import statement for the `Runner` class?

- **Zero-Context Success:** 0.00%
- **Contexts per Trial:** Avg 8.5 (Min: 3, Max: 15)
- **Final Max Uncertainty (SE):** 0.1575

| Status     |   Delta P | Source       |   Trials (In) | Document FQN                                                                                                          |
|------------|-----------|--------------|---------------|-----------------------------------------------------------------------------------------------------------------------|
| yg Helpful |      0.17 | retrieved    |            24 | google.adk.runners.Runner.execute                                                                                     |
| yg Helpful |      0.15 | gold_mined   |            21 | google.adk.runners.Runner                                                                                             |
| yg Helpful |      0.14 | retrieved    |            16 | google.adk.runners.InMemoryRunner                                                                                     |
| yg Helpful |      0.14 | random_noise |            18 | google.adk.code_executors.base_code_executor.BaseCodeExecutor.execute_code                                            |
| yg Helpful |      0.13 | retrieved    |            13 | google.adk.runners.Runner.close                                                                                       |
| yg Helpful |      0.13 | retrieved    |            14 | google.adk.runners.Runner.run                                                                                         |
| yg Helpful |      0.13 | retrieved    |            15 | google.adk.runners.Runner.run_async                                                                                   |
| yg Helpful |      0.12 | random_noise |            10 | google.genai.types.ReplayRequest                                                                                      |
| yg Helpful |      0.12 | random_noise |            11 | google.adk.sessions.in_memory_session_service.InMemorySessionService.list_sessions_sync                               |
| yg Helpful |      0.09 | retrieved    |            22 | google.adk.code_executors.built_in_code_executor                                                                      |
| yg Helpful |      0.07 | random_noise |            19 | google.genai.types.GetModelConfigDict                                                                                 |
| yg Helpful |      0.06 | random_noise |            18 | google.adk.tools.openapi_tool.auth.auth_helpers                                                                       |
| ⚪ Noise   |      0.03 | retrieved    |            13 | google.adk.code_executors.base_code_executor                                                                          |
| ⚪ Noise   |      0.03 | random_noise |            13 | google.genai.types.PreferenceOptimizationHyperParametersDict                                                          |
| ⚪ Noise   |      0.02 | retrieved    |            12 | google.adk.plugins.logging_plugin.LoggingPlugin.on_event_callback                                                     |
| ⚪ Noise   |      0.02 | random_noise |            23 | google.adk.tools.load_artifacts_tool.LoadArtifactsTool.process_llm_request                                            |
| ⚪ Noise   |      0.02 | random_noise |            12 | google.adk.cli.built_in_agents.tools.delete_files.delete_files                                                        |
| ⚪ Noise   |      0.01 | random_noise |            11 | google.adk.tools.computer_use                                                                                         |
| ⚪ Noise   |      0    | retrieved    |            10 | google.adk.a2a.converters.request_converter.AgentRunRequest                                                           |
| ⚪ Noise   |     -0.01 | random_noise |            19 | google.adk.memory.base_memory_service.BaseMemoryService.search_memory                                                 |
| ⚪ Noise   |     -0.02 | gold_mined   |            18 | google.adk.runners                                                                                                    |
| ⚪ Noise   |     -0.02 | retrieved    |            18 | google.adk.cli.adk_web_server.AdkWebServer.get_runner_async                                                           |
| ⚪ Noise   |     -0.03 | random_noise |            16 | google.adk.tools.base_authenticated_tool                                                                              |
| ⚪ Noise   |     -0.03 | random_noise |            16 | google.genai.live_music.AsyncMusicSession.set_weighted_prompts                                                        |
| ⚪ Noise   |     -0.04 | retrieved    |            15 | google.adk.a2a.utils.agent_to_a2a.create_runner                                                                       |
| ⚪ Noise   |     -0.04 | random_noise |            15 | google.adk.plugins.plugin_manager.PluginManager.register_plugin                                                       |
| ⚪ Noise   |     -0.05 | random_noise |             7 | vertexai.evaluation.metrics.metric_prompt_template.PairwiseMetricPromptTemplate.get_default_pairwise_evaluation_steps |
| ⚪ Noise   |     -0.05 | random_noise |             7 | google.adk.sessions.database_session_service.StorageEvent                                                             |
| ⚪ Noise   |     -0.06 | random_noise |            14 | google.genai.types.BatchJobDestinationDict                                                                            |
| ⚪ Noise   |     -0.08 | random_noise |            19 | google.genai.types.RagChunkDict                                                                                       |
| ❌ Toxic   |     -0.12 | random_noise |            16 | google.genai.types.CreateTuningJobConfig                                                                              |
| ❌ Toxic   |     -0.17 | retrieved    |             8 | google.adk.agents.run_config.RunConfig                                                                                |
| ❌ Toxic   |     -0.17 | random_noise |            13 | vertexai.preview.evaluation.utils.rate_limit                                                                          |
| ❌ Toxic   |     -0.2  | random_noise |            16 | google.genai.types.LiveConnectParametersDict                                                                          |

---

### Case: `configure_adk_features_mc:you_need_to_inspect_an_event_object_which_import_a`
**Query:** You need to inspect an `Event` object. Which import allows you to reference the `Event` class for type hinting?

- **Zero-Context Success:** 100.00%
- **Contexts per Trial:** Avg 8.9 (Min: 4, Max: 15)
- **Final Max Uncertainty (SE):** 0.1441

| Status   |   Delta P | Source       |   Trials (In) | Document FQN                                                                                    |
|----------|-----------|--------------|---------------|-------------------------------------------------------------------------------------------------|
| ⚪ Noise |      0.03 | retrieved    |            21 | google.adk.tools.openapi_tool.common.common.TypeHintHelper.get_type_hint                        |
| ⚪ Noise |      0.03 | retrieved    |            22 | google.adk.sessions.database_session_service.StorageEvent.from_event                            |
| ⚪ Noise |      0.02 | gold_mined   |            15 | google.adk.events.event                                                                         |
| ⚪ Noise |      0.02 | retrieved    |            16 | google.adk.evaluation.eval_case.InvocationEvents                                                |
| ⚪ Noise |      0.02 | retrieved    |            12 | google.adk.events.event_actions.EventActions                                                    |
| ⚪ Noise |      0.02 | retrieved    |            17 | google.adk.events.event_actions                                                                 |
| ⚪ Noise |      0.02 | retrieved    |            10 | google.adk.events.event.Event                                                                   |
| ⚪ Noise |      0.02 | retrieved    |            13 | google.adk.cli.adk_web_server.GetEventGraphResult                                               |
| ⚪ Noise |      0.02 | retrieved    |            15 | google.adk.tools.openapi_tool.common.common.TypeHintHelper                                      |
| ⚪ Noise |      0.02 | retrieved    |            13 | google.adk.a2a.converters.event_converter                                                       |
| ⚪ Noise |      0.02 | retrieved    |            16 | google.adk.cli.adk_web_server.AdkWebServer.event_generator                                      |
| ⚪ Noise |      0.02 | retrieved    |            12 | google.adk.evaluation.eval_case.InvocationEvent                                                 |
| ⚪ Noise |      0.02 | retrieved    |            10 | google.adk.apps.base_events_summarizer.BaseEventsSummarizer                                     |
| ⚪ Noise |      0.02 | random_noise |            16 | google.adk.cli.utils.service_factory.create_memory_service_from_options                         |
| ⚪ Noise |      0.02 | random_noise |            17 | google.genai.types.PhishBlockThreshold                                                          |
| ⚪ Noise |      0.02 | random_noise |             9 | google.genai.types.LiveMusicServerSetupCompleteDict                                             |
| ⚪ Noise |      0.02 | random_noise |             7 | vertexai.rag.rag_data.get_rag_engine_config                                                     |
| ⚪ Noise |      0.02 | random_noise |            12 | google.adk.cli.adk_web_server.InMemoryExporter                                                  |
| ⚪ Noise |      0.02 | random_noise |            18 | google.adk.auth.auth_credential.ServiceAccountCredential                                        |
| ⚪ Noise |      0.02 | random_noise |            10 | google.adk.code_executors.code_executor_context.CodeExecutorContext.get_execution_id            |
| ⚪ Noise |      0.02 | random_noise |            17 | vertexai.preview.evaluation.metrics.predefined_rubric_metrics.Pairwise                          |
| ⚪ Noise |      0.02 | random_noise |             7 | vertexai.preview.evaluation.metrics.rubric_based_metric.RubricBasedMetric                       |
| ⚪ Noise |      0.02 | random_noise |            17 | google.adk.tools.load_artifacts_tool                                                            |
| ⚪ Noise |      0.02 | random_noise |            13 | google.adk.apps.app.ResumabilityConfig                                                          |
| ⚪ Noise |      0.02 | random_noise |            17 | vertexai.agent_engines.list                                                                     |
| ⚪ Noise |      0.02 | random_noise |            17 | google.adk.memory.vertex_ai_memory_bank_service.VertexAiMemoryBankService.add_session_to_memory |
| ⚪ Noise |      0.02 | random_noise |             7 | google.adk.tools.google_tool.GoogleTool.run_async                                               |
| ⚪ Noise |      0.02 | random_noise |            19 | google.adk.evaluation.simulation.llm_backed_user_simulator.LlmBackedUserSimulator               |
| ⚪ Noise |      0.02 | random_noise |            16 | google.adk.flows.llm_flows.auto_flow                                                            |
| ⚪ Noise |      0.02 | random_noise |            16 | google.adk.cli.fast_api.register_processors                                                     |
| ⚪ Noise |     -0.04 | retrieved    |            23 | google.adk.sessions.database_session_service.StorageEvent.to_event                              |
| ⚪ Noise |     -0.06 | random_noise |            16 | google.adk.cli.conformance.cli_test.run_conformance_test                                        |
| ⚪ Noise |     -0.06 | random_noise |            16 | google.genai.types.GenerateContentConfigDict                                                    |
| ⚪ Noise |     -0.07 | gold_mined   |            15 | google.adk.models                                                                               |
| ⚪ Noise |     -0.07 | retrieved    |            14 | google.adk.tools.openapi_tool.common.common.TypeHintHelper.get_type_value                       |
| ⚪ Noise |     -0.07 | random_noise |            14 | google.genai.types.SupervisedTuningDatasetDistributionDatasetBucket                             |
| ⚪ Noise |     -0.09 | retrieved    |            11 | google.adk.events.event_actions.EventCompaction                                                 |

---
