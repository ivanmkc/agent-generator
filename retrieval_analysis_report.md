# Retrieval Dataset Analysis Report

## 1. Executive Summary

- **Total Cases Verified:** 1
- **Total Candidates Analyzed:** 34
- **Average Zero-Context Success Rate:** 0.00%

This report details the empirical relevance of documentation for each benchmark query, identifying 'Critical' documents (high Delta P) and 'Toxic' distractors.

## 2. Case Breakdown

### Case: `configure_adk_features_mc:which_is_the_correct_import_statement_for_the_runn`
**Query:** Which is the correct import statement for the `Runner` class?

- **Zero-Context Success:** 0.00%
- **Final Max Uncertainty (SE):** 0.0940

| Status   |   Delta P | Source       |   Trials (In) | Document FQN                                                                              |
|----------|-----------|--------------|---------------|-------------------------------------------------------------------------------------------|
| ⚪ Noise |         0 | gold_mined   |            18 | google.adk.runners                                                                        |
| ⚪ Noise |         0 | gold_mined   |            12 | google.adk.runners.Runner                                                                 |
| ⚪ Noise |         0 | retrieved    |            17 | google.adk.runners.Runner.execute                                                         |
| ⚪ Noise |         0 | retrieved    |            19 | google.adk.runners.Runner.close                                                           |
| ⚪ Noise |         0 | retrieved    |            19 | google.adk.runners.InMemoryRunner                                                         |
| ⚪ Noise |         0 | retrieved    |            16 | google.adk.a2a.utils.agent_to_a2a.create_runner                                           |
| ⚪ Noise |         0 | retrieved    |            16 | google.adk.runners.Runner.run                                                             |
| ⚪ Noise |         0 | retrieved    |            16 | google.adk.cli.adk_web_server.AdkWebServer.get_runner_async                               |
| ⚪ Noise |         0 | retrieved    |            17 | google.adk.agents.run_config.RunConfig                                                    |
| ⚪ Noise |         0 | retrieved    |            16 | google.adk.code_executors.built_in_code_executor                                          |
| ⚪ Noise |         0 | retrieved    |            22 | google.adk.runners.Runner.run_async                                                       |
| ⚪ Noise |         0 | retrieved    |            19 | google.adk.code_executors.base_code_executor                                              |
| ⚪ Noise |         0 | retrieved    |            21 | google.adk.plugins.logging_plugin.LoggingPlugin.on_event_callback                         |
| ⚪ Noise |         0 | retrieved    |            17 | google.adk.a2a.converters.request_converter.AgentRunRequest                               |
| ⚪ Noise |         0 | random_noise |            22 | google.genai.types.FunctionResponsePart                                                   |
| ⚪ Noise |         0 | random_noise |            12 | google.adk.agents.invocation_context.InvocationContext.set_agent_state                    |
| ⚪ Noise |         0 | random_noise |            19 | google.adk.cli.conformance.cli_test.run_conformance_test                                  |
| ⚪ Noise |         0 | random_noise |            16 | google.adk.agents.llm_agent_config.LlmAgentConfig                                         |
| ⚪ Noise |         0 | random_noise |            14 | google.adk.tools.retrieval.files_retrieval.FilesRetrieval                                 |
| ⚪ Noise |         0 | random_noise |            21 | google.adk.tools.bigtable.bigtable_toolset.BigtableToolset                                |
| ⚪ Noise |         0 | random_noise |            19 | google.genai.types.DeleteCachedContentResponseDict                                        |
| ⚪ Noise |         0 | random_noise |            20 | google.genai.types.HarmCategory                                                           |
| ⚪ Noise |         0 | random_noise |            20 | vertexai.preview.reasoning_engines.templates.langgraph.LanggraphAgent.register_operations |
| ⚪ Noise |         0 | random_noise |            18 | google.adk.evaluation.eval_rubrics.Rubric                                                 |
| ⚪ Noise |         0 | random_noise |            18 | google.genai.types.DeleteDocumentConfig                                                   |
| ⚪ Noise |         0 | random_noise |            17 | google.adk.cli.adk_web_server.CreateEvalSetRequest                                        |
| ⚪ Noise |         0 | random_noise |            19 | google.adk.plugins.logging_plugin.LoggingPlugin                                           |
| ⚪ Noise |         0 | random_noise |            14 | google.genai.types.Interval                                                               |
| ⚪ Noise |         0 | random_noise |            19 | google.genai.types.UploadToFileSearchStoreOperation.from_api_response                     |
| ⚪ Noise |         0 | random_noise |            13 | google.adk.cli.agent_graph.build_graph                                                    |
| ⚪ Noise |         0 | random_noise |            17 | google.adk.tools.retrieval.base_retrieval_tool.BaseRetrievalTool                          |
| ⚪ Noise |         0 | random_noise |            18 | google.adk.evaluation.in_memory_eval_sets_manager.InMemoryEvalSetsManager.create_eval_set |
| ⚪ Noise |         0 | random_noise |            14 | google.adk.tools.load_artifacts_tool.LoadArtifactsTool.run_async                          |
| ⚪ Noise |         0 | random_noise |            13 | google.genai.types.Scale                                                                  |

---
