<!-- capsule-v2 -->
# Conversation tracker hydration — how does a resumed run re-seed dedupe state without replaying or losing items?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When a run resumes from serialized state, how do you rebuild the server-conversation tracker's dedupe views from rebuilt objects (whose Python identities no longer match), keep the `previous_response_id` chain alive across id-less provider responses, and keep locally-produced tool outputs that never reached the server still sendable?

## hydrate_from_state source-aware seeding + unsent_tool_call_ids skip
**Path/Symbol:** `src/agents/run_internal/oai_conversation.py:` `OpenAIServerConversationTracker.hydrate_from_state` (:177–348); `src/agents/run_internal/agent_runner_helpers.py:` `get_unsent_tool_call_ids_for_interrupted_state` (:207–245); call site `src/agents/run_internal/run_loop.py` (:1059–1065).
**Signature:** `hydrate_from_state(*, original_input: str | list[TResponseInputItem], generated_items: list[RunItem], model_responses: list[ModelResponse], session_items: list[TResponseInputItem] | None = None, unsent_tool_call_ids: set[str] | None = None) -> None`.
**Data Shape:** seeds the tracker's views — `server_item_ids`, `server_tool_call_ids` (call-ids WITH an output payload), `sent_item_fingerprints`, `server_output_fingerprints`, `restored_anonymous_tool_search_fingerprints`, `accepted_input_item_ids`, `sent_items` (object identity), `previous_response_id`; ends with `sent_initial_input=True`, `remaining_initial_input=None`, `primed_from_state=True`.

### Decisive source
```python
if self.sent_initial_input:
    return                                   # one-shot hydration
# (a) original input: fingerprints + ids ONLY — identity deliberately excluded
for item in ItemHelpers.input_to_new_input_list(normalized_input):
    ...
    if item_id is not None: self.server_item_ids.add(item_id)
    if fp: self.sent_item_fingerprints.add(fp)
self.sent_initial_input = True
self.remaining_initial_input = None
# (b) responses: LAST non-None response_id wins, not model_responses[-1]
for response in model_responses:
    if response.response_id is not None:
        latest_response_id = response.response_id
    for output_item in response.output:
        _track_object_once(self.server_items, output_item)
        ...
        if isinstance(call_id, str) and has_output_payload:
            self.server_tool_call_ids.add(call_id)
if self.conversation_id is None and latest_response_id is not None:
    self.previous_response_id = latest_response_id
# (d) generated items: unsent local outputs stay sendable
if isinstance(call_id, str) and has_output_payload and call_id in unsent_tool_call_ids:
    continue                                  # NOT tracked → will be sent again
should_mark = (item_id is not None
    or (has_call_id and (has_output_payload or is_tool_call_item))
    or is_input_item or is_tool_search_item)
...
if is_input_item:
    self.accepted_input_item_ids.add(run_item.input_id)   # inputs join by input_id, not fingerprint
```

**Flow:** on resume the runner hydrates the tracker once (guarded by `sent_initial_input`) from four sources, each contributing to exactly the views it can prove. (a) The original input was serialized and rebuilt, so object identity is unstable and could collide with freshly allocated items — only content fingerprints and server item ids are seeded, and `remaining_initial_input` is cleared. (b) Model responses are walked in order keeping the LAST non-None `response_id` (a trailing non-Responses-provider response has `response_id=None` and must not break the chain — mirroring live `track_server_items`, which skips None updates); output objects are tracked once by identity, their ids into `server_item_ids`, and call-ids that carry an output payload into `server_tool_call_ids`; when there is no explicit conversation, `previous_response_id` is set to that latest id. (c) Session items contribute the same triple (ids, call-ids-with-output, fingerprints). (d) Generated run items get the richest rules: an item whose call_id has an output payload AND whose call_id is in `unsent_tool_call_ids` is skipped entirely (its local output never reached the server, so it must be sent again); otherwise items with an id, call-ids with outputs or tool/handoff calls, InputItems, or tool-search items are marked — InputItems register `accepted_input_item_ids` by `run_item.input_id` instead of a fingerprint, and tool-search outputs additionally land in `server_output_fingerprints`. `unsent_tool_call_ids` come from the interrupted state: for a run-again step, all call-ids in the last model response's output; for an interruption, call-ids across all seven tool-run groups of the last processed response.
**Invariant:** a resumed run neither replays acknowledged content nor loses sendable pending outputs — every view is seeded only from sources that can prove it, the response chain survives id-less providers, and hydration is one-shot so later live tracking cannot double-seed.
**Probe:** `tests/test_oaiconv_resume_response_id.py::test_hydrate_from_state_uses_latest_non_none_response_id` (:18 — `[resp_first, resp_second, None]` yields `previous_response_id == "resp_second"`), `tests/test_server_conversation_tracker.py::test_hydrate_from_state_preserves_unsent_outputs_from_interrupted_turn` (:102 — `"call_DIAG" not in tracker.server_tool_call_ids` and the prepared delta keeps `["call_DIAG", "call_CLEANUP1", "call_CLEANUP2"]`), `::test_hydrate_from_state_does_not_track_string_initial_input_by_object_identity` (:214), `::test_hydrate_from_state_does_not_track_list_initial_input_by_object_identity` (:231).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "oai_conversation.py", query: "hydrate from state unsent tool call ids", limit: 20 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.run_internal.oai_conversation.OpenAIServerConversationTracker.hydrate_from_state" });
```

## Verdict
Adopt source-aware hydration for any server-side-conversation dedupe tracker: per-source view contributions (rebuilt input → fingerprints only; responses → last-id-bearing chain; session → triple; generated → full rules with an explicit unsent set), the one-shot guard, and the "skip what never reached the server" rule for interrupted local outputs. Adapt the view names and the interrupted-state extraction. Omit the anonymous-tool-search fingerprint views if you have no tool-search surface. Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); :177–348 read whole from checkout at fe45b415.
