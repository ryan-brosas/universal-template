<!-- capsule-v2 -->
# Session rewind protocol — how are retry-owned items rolled back without corrupting shared history?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** When a model request must be retried, how do you undo the session writes the failed attempt caused?

## Exact-suffix rewind + stray sweep
**Path/Symbol:** `src/agents/run_internal/session_persistence.py:` `rewind_session_items` (:727–831), `_rewind_session_tail_suffix` (:978–1040), `_restore_popped_session_items` (:1043–1065), `wait_for_session_cleanup` (:834–876), `_collect_retry_owned_tail_serializations` (:1068–1098).
**Signature:** `async def rewind_session_items(session, items, server_tracker=None, *, wrapper=None) -> None`.
**Data Shape:** items fingerprinted (`fingerprint_input_item`, ids optionally ignored for conversation-backed sessions); pops return one item at a time via `session.pop_item()`.

### Decisive source
```python
if tail_serializations != list(expected_serializations):
    logger.warning(mismatch_warning)
    return False
popped_items: list[TResponseInputItem] = []
for expected in reversed(expected_serializations):
    result = await _session_pop_item(session, wrapper=wrapper)
    if popped_serialized != expected:
        await _restore_popped_session_items(session, popped_items, wrapper=wrapper)
        logger.warning(mismatch_warning)
        return False
```
After a successful rewind: `wait_for_session_cleanup` polls (≤5 attempts, 0.1s×n backoff) that no target fingerprint remains in a `len(targets)+2` window. Server-tracked variant: peek latest item; if its id is NOT in `server_tracker.server_item_ids`, collect the contiguous retry-owned suffix (fingerprints ∈ `server_tracker.sent_item_fingerprints`, walking back until a known server item) and strip it too; ANY unrelated item in the walk aborts the whole cleanup.

**Flow:** fingerprint targets → read exact-length tail → compare serialized suffix → pop one-by-one from newest, verifying each fingerprint → on ANY mismatch/None/exception restore already-popped items (reversed) and abort with warning → verify absence → optional server-stray strip. Best-effort by design: divergence never raises into the retry path.

**Invariant:** Never pop past an item you cannot prove is yours; restore-on-failure keeps the store consistent even when pop itself fails mid-sequence; rewind is advisory — the retry proceeds even if the store kept stale items.

**Probe:** `tests/memory/test_session_context_wrapper.py::test_retry_rewind_restores_partial_pops_in_the_same_context_scope` (:288); `tests/test_agent_runner.py::test_rewind_strips_only_retry_owned_tail_items_before_known_server_item` (:3777); `tests/test_agent_runner.py::test_non_streamed_model_retry_does_not_rewind_committed_session_input` (:3454).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "rewind session tail suffix retry owned stray", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verify-then-pop-then-restore for transactional semantics over any pop-only store; adapt fingerprints to your equality notion; omit the server-tracker stray sweep if you have no server-side item registry.
