# Todo List

# Active

# Completed
## Generator
- [x] Implement `reconstruct_constructor_signature` in `TargetRanker` to fix missing init signatures for Pydantic models. Now supports dynamic detection of `init=False` fields (Pydantic/Dataclasses) and explicit exclusion of internal framework fields.

## Tools
- [x] `search_adk_knowledge` with param ("query":"context") is broken: "Error executing tool search_adk_knowledge: 'tuple' object has no attribute 'get'". Fixed by correcting the sort lambda in `KeywordSearchProvider`.

## Benchmark Cases
- [x] `api_understanding:which_top_level_wrapper_class_is_used_to_attach_pl`: Refined to be less ambiguous, specifying it refers to global application settings like plugins and event compaction.
- [x] `configure_adk_features_mc:how_do_you_specify_that_a_tool_function_should_not`: Modified Option A to return `None` and Option D to an incorrect value. Updated explanation to reflect that `None` return indicates a side-effect tool.

## Viewer
- [x] Merge messages logic joins content with newlines (`\n`), which can break words/JSON if the original content was not line-delimited (e.g. streaming chunks or partial outputs). It should join with an empty string.
- [x] Ensure merged messages and model responses render actual newlines correctly (e.g., using `white-space: pre-wrap` or converting `\n` to Markdown line breaks).
- [x] Code blocks in Viewer had infinite width/no wrap. Fixed by injecting custom CSS into `benchmark_viewer.py`.

## MCP Server
- [x] Fix bug where `read_adk_source_code` and `inspect_adk_symbol` fail for class methods (e.g. `BaseLlmConnection.send_history`) because they only look up top-level symbols in the index/AST.

## Viewer (Previous)
- [x] 'Generation Error' tab seems to be erroneously showing the validation error.
- [x] 'Validation Error' tab seems to just show unrelated: Attempt Metadata, Token usage and other execution metadata.
- [x] Viewer? Logger?: Tool Call shows { "fqn":"google.adk.events.event.Event" } returns "No result recorded.". However, there is clearly a subsequent "System Event: TraceEventType.TOOL_RESULT" with the result there. So the tool call should have shown this result. What's going on?

## Runner
- [x] Remove the adk-python repo from 'gemini-cli:mcp_adk_agent_runner_ranked_knowledge' and bundle it into the MCP boundary to force it to only use ranked targets.

## Viewer
- [x] Fix TraceLogEvent AttributeError in merge_consecutive_events (object has no attribute 'get').
- [x] Consecutive `TraceEventType.MESSAGE` from the same role should be merged into a single message.
- [x] CLI Output should be merged.
- [x] CLI Output should be in a separate tab, not trace logs.
- [x] There are unneeded headings in the AI report navigator. Fix and write tests to prevent regression.

Copyright 2025 Google LLC
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may in obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
...`
Copyright 2025 Google LLC
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
...`
Copyright 2025 Google LLC
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BAS...`
9. Report Generation Metadata


## Tools
- [x] `search_adk_knowledge` should have a semantic search ability (Implemented BM25 probabilistic retrieval as a lightweight semantic search alternative).

## Benchmark Cases
- [x] `api_understanding:what_is_the_fundamental_data_structure_for_convers` rewritten to be less ambiguous.
- [x] `api_understanding:which_class_provides_the_capability_to_add_plugins` rewritten to be less ambiguous.
- [x] `configure_adk_features_mc:you_want_to_automatically_summarize_old_events_to_`: Fixed ambiguity by changing option D to a clearly incorrect value.

## Benchmark validation infra
- [x] For the benchmark validation, if the parsing of JSON doesn't work right away. Fallback on extracting from backticks ``` ``` and then parsing that. This will fix some issues like:                                                                                   │
│                                                                                                                                        │
│   Explanation: The agent correctly identified the solution ('BasePlugin') and constructed a valid JSON object representing the         │
│   answer. However, the final response string emitted by the agent contained a lengthy conversational narrative ('Okay, I need to find  │
│   an ADK plugin class...') preceding the JSON block. The benchmark's validation system attempted to parse the entire response string   │
│   as JSON, resulting in a parsing error ('expected value at line 1 column 1') because the input did not start with a valid JSON        │
│   character.