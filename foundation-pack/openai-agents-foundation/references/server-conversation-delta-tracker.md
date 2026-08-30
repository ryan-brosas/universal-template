<!-- capsule-v2 -->
# Server conversation delta tracker — how does a conversation-aware run compute safe deltas across retries and resumes without resending or dropping input?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When a server-managed conversation means each request should carry only NEW deltas, how do you track what has been sent/acknowledged so that (a) a failed request can be replayed without losing its input, (b) a successful retry restores exactly the tracking state the next turn expects, and (c) a resumed run with rebuilt objects still dedupes correctly?

## Three dedupe views + rewind-before-replay / re-mark-after-success cycle
**Path/Symbol:** `src/agents/run_internal/oai_conversation.py:` `OpenAIServerConversationTracker` (:124–174), `hydrate_from_state` (:177–348), `track_server_items` (:350–392), `mark_input_as_sent` (:394–427), `validate_pending_input_filter` (:429–493), `rewind_input` (:495–516), `prepare_input` (:518–645), `_consume_prepared_item_source` (:647–670), `_delivery_source` (:673–680), `mark_input_as_accepted` (:682–692); runner cycle `src/agents/run_internal/run_loop.py` :2154–2162 (validate + mark sent after filter), :2214–2216 (`rewind_model_request`), :2308–2313 (streamed success re-mark), :2628–2634 (non-streamed success re-mark), :1854 (post-turn `track_server_items`); retry sites `src/agents/run_internal/model_retry.py` :637, :677, :848, :887 (`await rewind()` before each replay).
**Signature:** `prepare_input(original_input, generated_items) -> list[TResponseInputItem]`; `mark_input_as_sent(items) -> None`; `rewind_input(items) -> None`; `mark_input_as_accepted(items) -> set[str]`; `track_server_items(model_response) -> None`.
**Data Shape:** three complementary views — object identity lists (`sent_items`, `server_items`: real objects kept alive, never `id()` ints, so a later allocation cannot reuse a stale address), stable provider id sets (`server_item_ids`, `server_tool_call_ids` — call-ids only when the item carries an output payload; `FAKE_RESPONSES_ID` placeholders ignored), content fingerprint sets (`sent_item_fingerprints`, `server_output_fingerprints`, `restored_anonymous_tool_search_fingerprints`) for rebuilt objects after resume; plus `remaining_initial_input` (pending initial items not yet delivered) and `accepted_input_item_ids` (pending RunState input ids present in a successful server request).

### Decisive source
```python
# run_loop.py — the per-turn contract around the model call:
server_conversation_tracker.validate_pending_input_filter(filtered.input)
server_conversation_tracker.mark_input_as_sent(filtered.input)   # after filtering
...
async def rewind_model_request() -> None:
    if server_conversation_tracker is not None:
        server_conversation_tracker.rewind_input(filtered.input)
...
# on success (both streamed :2308-2313 and non-streamed :2628-2634):
server_conversation_tracker.mark_input_as_sent(filtered.input)
server_conversation_tracker.mark_input_as_accepted(filtered.input)
server_conversation_tracker.track_server_items(new_response)
```

**Flow:** `prepare_input` computes the delta — it skips generated items whose `input_id` is in `accepted_input_item_ids`, whose item id is in `server_item_ids`, whose call-id-with-output is in `server_tool_call_ids`, that are identity-tracked in `sent_items`/`server_items`, or whose fingerprint is already known (fingerprint skips only apply once `primed_from_state` for anonymous items) — and registers prepared→source mappings keyed by `id(prepared)` WITH an identity check (`direct_entry[0] is item`) plus a fingerprint fallback list → after `call_model_input_filter` runs, `validate_pending_input_filter` raises UserError when a filter rewrite's pending-input lineage is ambiguous (a reconstructed item matching multiple pending sources incl. an id-less one), then `mark_input_as_sent` resolves each filtered item back to its SOURCE object via `_delivery_source` and marks the source, pruning `remaining_initial_input` by identity then fingerprint → the retry helpers (`get_response_with_retry`/`stream_response_with_retry`) call `await rewind()` BEFORE every replay attempt: `rewind_input` untracks the sources from `sent_items`, discards their fingerprints only when they had no input_id, and re-queues them at the FRONT of `remaining_initial_input` → on success the runner re-marks sent+accepted (restoring exactly the pre-failure tracking state) and `track_server_items` records server-acknowledged outputs (objects, ids, call-ids-with-output, fingerprints), prunes `remaining_initial_input` by fingerprint against what the server just acknowledged, and advances `previous_response_id` to the latest response id while `conversation_id` is None → `hydrate_from_state` seeds all views from serialized state on resume (fingerprints instead of identity, since rebuilt objects collide; `unsent_tool_call_ids` keeps not-yet-sent outputs sendable).
**Invariant:** delta computation is idempotent under retry — a failed request never permanently consumes input (rewind before replay), a successful retry restores exactly the tracking state the next turn's delta expects (re-mark after success), and no item is ever sent twice or dropped across pause/resume/retry; ambiguous filter rewrites fail loud rather than mis-attribute pending input.
**Probe:** `tests/test_server_conversation_tracker.py::test_mark_input_as_sent_and_rewind_input_respects_remaining_initial_input` (:249 — sent prunes remaining to None, rewind re-queues exactly the rewound item), `::test_mark_input_as_sent_ignores_stale_id_for_rebuilt_filtered_item` (:264 — monkeypatched stale `id()` collision still marks the real source object, not the stale one), `::test_track_server_items_filters_remaining_initial_input_by_fingerprint` (:706 — server-acknowledged equivalent prunes pending by fingerprint), `::test_prepare_input_does_not_skip_fake_response_ids` (:729 — FAKE ids never dedupe).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "oai_conversation.py", query: "rewind mark_input_as_sent remaining_initial_input", limit: 20 });
await mcp.codebase_memory.trace_path({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.run_internal.oai_conversation.OpenAIServerConversationTracker.rewind_input", direction: "inbound" });
```

## Verdict
Adopt the three-view dedupe (live identity / stable provider ids / content fingerprints) plus the rewind-before-replay + re-mark-after-success cycle for any client that must send incremental deltas against a server-managed conversation. Adapt the fingerprint function and the "call-id counts only with an output payload" rule to your API's ack semantics. Omit the fingerprint view entirely if you never resume from serialized state (identity + provider ids suffice for in-process retries). Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); oai_conversation.py read whole (692 ln) from checkout at fe45b415.
