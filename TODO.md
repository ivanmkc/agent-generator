# Todo List
- Check if fix_errors:08_custom_agent needs CustomConditionalAgent to have sub_agents passed in, such as:
- Can we create one canonical agent that uses 99% of the API, with comments?

```
  root_agent = CustomConditionalAgent(
      name="custom_conditional_agent",
      agent_a=agent_a,
      agent_b=agent_b,
      sub_agents=[agent_a, agent_b],
  )
```

or can sub_agents be omitted. Add a unit-test to test both out and update the unfixed, fixed and test accordingly.

- api_understanding:which_class_is_used_to_run_multiple_agents_concurr: is ambiguous as Runner can technically run multiple agents using run_async. reword question to make it clear 'what type of agent is used to run agents concurrently'.
- Seems like list_adk_modules is only called with page=1. At what page do we see a cumulative usage of 99% or more?
- Hm, predict_runtime_behaviour with code_snippet_ref are problematic. Some are used for validation that the question is correct. Some are embedded into the question and shown to the user. Please go through each and check if each makes sense.
- double check that predict_runtime_behavior_mc:duplicate_agent_name: Looks like validate_sub_agents_unique_names with log a warning.
- double check: predict_runtime_behavior_mc:event_extra_fields_error
- Improve: predict_runtime_behavior_mc:tool_session_id_injection: A little ambiguous.
- api_understanding:which_specific_plugin_class_is_designed_to_observe: The answer might also be satisfied with google.adk.plugins.bigquery_agent_analytics_plugin.BigQueryAgentAnalyticsPlugin. We should rethink this question to be unambiguous.
- configure_adk_features_mc:which_class_allows_you_to_define_a_tool_from_an_op: The 'correct' answer, OpenAPITool, does not exist. OpenAPIToolset does though. This question is currently wrong.
- configure_adk_features_mc:you_are_implementing_a_custom_tool_which_method_mu: This question is probably wrongly answered. Please check against code, write a test and fix.

# Prioritized Features (From Design Docs)
- [ ] **Implement Robust LLM-Based JSON Extraction** (`docs/design_docs/llm_json_parsing.md`): Create a `JsonSanitizer` that uses a lightweight LLM to repair malformed JSON output from agents, reducing schema violation failures.
- [ ] **Implement Search Suggestions** (`docs/design_docs/search_suggestions.md`): Update `search_adk_knowledge` to return "Did you mean?" suggestions using fuzzy matching when exact search yields zero results.
- [ ] **Implement Usage-Ranked Pagination** (`docs/design_docs/list_modules_pagination.md`): Modify `list_adk_modules` to return high-usage classes on Page 1 instead of alphabetical sorting.
- [ ] **Optimize Analysis Report Generation** (`docs/design_docs/optimize_analysis_report.md`): Implement caching and adaptive concurrency to speed up the `generate_ai_report.py` pipeline.
- [ ] **Question Quality Verifier** (`docs/design_docs/question_quality_verifier.md`): Build an agent loop to automatically audit benchmark questions for ambiguity and correctness.

# Active

# Completed
## Generator
- [x] Fix create_hybrid_generator_v47 and add to unified integration tests.
- [x] Implement `reconstruct_constructor_signature` in `TargetRanker` to fix missing init signatures for Pydantic models. Now supports dynamic detection of `init=False` fields (Pydantic/Dataclasses) and explicit exclusion of internal framework fields.

## Tools
- [x] Reorganize tools/ dir and flag redundant/obsolete files. Also check cli. Dismabiguate generate_forensic_report.py and generate_benchmark_report.py. (Renamed `audit_failures.py` to `generate_static_report.py`).
- [x] `search_adk_knowledge` with params {"query":"ToolConfig"} returned "No matches found". Fixed by improving BM25 tokenization for FQNs.
- [x] `search_adk_knowledge` with param ("query":"context") is broken: "Error executing tool search_adk_knowledge: 'tuple' object has no attribute 'get'". Fixed by correcting the sort lambda in `KeywordSearchProvider`.
- [x] `search_adk_knowledge` should have a semantic search ability (Implemented BM25 probabilistic retrieval as a lightweight semantic search alternative).

## Benchmark Cases
- [x] diagnose_setup_errors_mc:cache_ttl_string: Answer seems wrong as ttl is not a field, it should be ttl_seconds. (Updated question).
- [x] diagnose_setup_errors_mc:compaction_interval_zero: Please double check the answer and verify with code. (Updated answer to D: No error).
- [x] diagnose_setup_errors_mc:sequential_empty_subagents: Is worded ambiguously. (Clarified wording).
- [x] `api_understanding:which_top_level_wrapper_class_is_used_to_attach_pl`: Refined to be less ambiguous, specifying it refers to global application settings like plugins and event compaction.
- [x] `configure_adk_features_mc:how_do_you_specify_that_a_tool_function_should_not`: Modified Option A to return `None` and Option D to an incorrect value. Updated explanation to reflect that `None` return indicates a side-effect tool.
- [x] `api_understanding:what_is_the_fundamental_data_structure_for_convers` rewritten to be less ambiguous.
- [x] `api_understanding:which_class_provides_the_capability_to_add_plugins` rewritten to be less ambiguous.
- [x] `configure_adk_features_mc:you_want_to_automatically_summarize_old_events_to_`: Fixed ambiguity by changing option D to a clearly incorrect value.

## Viewer
- [x] Viewer: Do we need both a generation error tab and a validation error tab? Consolidated into universal 'Errors' tab.
- [x] Viewer's 'Select Run' dropdown should signify each row's state (pending, completed, failed, etc). (Implemented).
- [x] Merge messages logic joins content with newlines (`\n`), which can break words/JSON if the original content was not line-delimited (e.g. streaming chunks or partial outputs). It should join with an empty string.
- [x] Ensure merged messages and model responses render actual newlines correctly (e.g., using `white-space: pre-wrap` or converting `\n` to Markdown line breaks).
- [x] Code blocks in Viewer had infinite width/no wrap. Fixed by injecting custom CSS into `benchmark_viewer.py`.
- [x] Fix TraceLogEvent AttributeError in merge_consecutive_events (object has no attribute 'get').
- [x] Consecutive `TraceEventType.MESSAGE` from the same role should be merged into a single message.
- [x] CLI Output should be merged.
- [x] CLI Output should be in a separate tab, not trace logs.
- [x] There are unneeded headings in the AI report navigator. Fix and write tests to prevent regression.
- [x] 'Generation Error' tab seems to be erroneously showing the validation error.
- [x] 'Validation Error' tab seems to just show unrelated: Attempt Metadata, Token usage and other execution metadata.
- [x] Viewer? Logger?: Tool Call shows { "fqn":"google.adk.events.event.Event" } returns "No result recorded.". However, there is clearly a subsequent "System Event: TraceEventType.TOOL_RESULT" with the result there. So the tool call should have shown this result. What's going on?

## Documentation
- [x] Create design doc for: Optimize analysis report generation.
- [x] Write a design doc for other list_adk_modules pagination strategies.
- [x] Write a design doc on how to return suggestions for 'close matches'.
- [x] Write a design doc to add a LLM JSON parsing step.
- [x] Write a design doc for a question quality verifier.

## MCP Server
- [x] Fix bug where `read_adk_source_code` and `inspect_adk_symbol` fail for class methods (e.g. `BaseLlmConnection.send_history`) because they only look up top-level symbols in the index/AST.

## Runner
- [x] Remove the adk-python repo from 'gemini-cli:mcp_adk_agent_runner_ranked_knowledge' and bundle it into the MCP boundary to force it to only use ranked targets.

## Benchmark validation infra
- [x] For the benchmark validation, if the parsing of JSON doesn't work right away. Fallback on extracting from backticks ``` ``` and then parsing that.
