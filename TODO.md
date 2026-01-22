# Todo List

## Viewer
- [x] Consecutive `TraceEventType.MESSAGE` from the same role should be merged into a single message.
- [x] CLI Output should be merged.
- [x] CLI Output should be in a separate tab, not trace logs.

## Tools
- [x] `search_adk_knowledge` should have a semantic search ability (Implemented BM25 probabilistic retrieval as a lightweight semantic search alternative).

## Benchmark Cases
- [x] `api_understanding:what_is_the_fundamental_data_structure_for_convers` rewritten to be less ambiguous.
- [x] `api_understanding:which_class_provides_the_capability_to_add_plugins` rewritten to be less ambiguous.
- [x] `configure_adk_features_mc:you_want_to_automatically_summarize_old_events_to_`: Fixed ambiguity by changing option D to a clearly incorrect value.