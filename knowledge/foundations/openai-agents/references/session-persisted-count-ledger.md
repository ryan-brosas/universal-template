<!-- capsule-v2 -->
# Session persisted-count ledger — how do streaming retries avoid duplicating turn items in the session?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** Given a turn that can be saved multiple times (retry paths, resume paths), what makes each save idempotent?

## Count-based slicing + missing-output rescue
**Path/Symbol:** `src/agents/run_internal/session_persistence.py:` `save_result_to_session` (:545–698); counter lifecycle at run_loop.py :1454–1458 (zeroed per turn), :1703–1706 (zeroed on RunAgain).
**Signature:** `async def save_result_to_session(session, original_input, new_items, run_state=None, *, response_id=None, reasoning_item_id_policy=None, store=None, wrapper=None) -> int`.
**Data Shape:** `already_persisted = run_state._current_turn_persisted_item_count`; returns number newly persisted; counter advanced to `already_persisted + saved_run_items_count`.

### Decisive source
```python
new_run_items = new_items[already_persisted:]
if run_state is not None and new_items and new_run_items:
    missing_outputs = [
        item for item in new_items
        if item.type == "tool_call_output_item" and item not in new_run_items
    ]
    if missing_outputs:
        new_run_items = missing_outputs + new_run_items
```
Dedup within one save: fingerprints (`fingerprint_input_item`, repr fallback) of new items counted against the full save batch (`deduplicate_input_items_preferring_latest(input + new)`), counting only occurrences that will actually be stored; the count advances by that number even when nothing is written. Compaction-aware sessions: if this turn produced LOCAL tool/handoff outputs, compaction is DEFERRED for this response id (`_defer_compaction`) and forced later once no local outputs remain (`_get_deferred_compaction_response_id`).

**Flow:** slice off already-persisted prefix → rescue stranded tool OUTPUTS (their calls may already be persisted but outputs must never lag) → convert RunItems→input items under reasoning-id policy → fingerprint-count against save batch → add → advance counter → maybe defer/force compaction.

**Invariant:** A tool output must never be persisted without (eventually) its call and vice versa — hence the rescue prepend; the counter is authoritative per TURN (reset at turn start and at RunAgain) and travels through resume closures; saves must be safe to repeat with growing lists.

**Probe:** `tests/test_agent_runner_streamed.py::test_streaming_resume_with_session_does_not_duplicate_items` (:2192); compaction deferral pinned by `tests/memory/test_openai_responses_compaction_session.py` (`test_run_compaction_*` family :169–284+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "save result to session persisted item count missing tool outputs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt count-slicing plus output-rescue for any append-only history with retryable writes; adapt fingerprinting to your serialization; omit compaction hooks if your backend lacks server-side compaction.
