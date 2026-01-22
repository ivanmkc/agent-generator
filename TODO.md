# Todo List

## Viewer
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