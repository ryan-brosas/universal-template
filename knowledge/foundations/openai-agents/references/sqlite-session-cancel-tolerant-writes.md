<!-- capsule-v2 -->
# SQLiteSession cancel-tolerant writes — how does a session write survive caller cancellation and a poisoned connection?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** What is the exact behavior when an asyncio cancellation lands during (or just after) a SQLite history mutation?

## `_await_mutation` shield + connection quarantine
**Path/Symbol:** `src/agents/memory/sqlite_session.py:` `_await_mutation` (:19–38), `_write_connection` (:153–164), `_invalidate_connection` (:166–184), file-lock refcounting (:50–52, :116–140), corrupt-row window expansion in `get_items` (:305–325), pop corruption loop (:388–409).
**Signature:** `async def _await_mutation(awaitable: Awaitable[_T]) -> _T`.
**Data Shape:** mutations run via `asyncio.to_thread`; per-file class-level RLock registry keyed by resolved path with refcounts; memory DBs use one shared connection + instance RLock.

### Decisive source
```python
async def _await_mutation(awaitable):
    task = asyncio.ensure_future(awaitable)
    cancellation = None
    while not task.done():
        try:
            await asyncio.wait({task})
        except asyncio.CancelledError as exc:
            if cancellation is None:
                cancellation = exc        # absorb repeats; keep waiting for the outcome
    try:
        result = task.result()
    except BaseException:
        if cancellation is not None:
            raise cancellation from None  # known-outcome failure: surface CANCELLATION
        raise
    if cancellation is not None:
        raise cancellation from None      # success then cancelled: still honour cancel
    return result
```
Write path: any exception inside `_write_connection` triggers rollback; if rollback ITSELF fails the connection is closed-and-evicted (close failure ⇒ quarantined set); a memory-DB eviction closes the whole session (`_closed = True`). Reads tolerate corrupt JSON by expanding the fetch window ×2 until `limit` valid items are found, and `pop_item` deletes-and-returns via `DELETE ... RETURNING` looping past corrupted rows.

**Flow:** schedule mutation in worker thread → swallow repeated CancelledError while polling → on completion raise FIRST cancellation regardless of outcome (outcome known ⇒ no lost write) → writers always leave transactions rolled back or connections evicted → close() re-raises the FIRST connection-close error after closing the rest, releases file locks only when nothing remains quarantined.

**Invariant:** A cancelled mutation must never leave an unknown outcome: either the write committed (caller learns it was cancelled) or it failed (cancellation masks the secondary error). Lock lifetime is tied to connection health, not object lifetime.

**Probe:** `tests/memory/test_session.py::test_await_mutation_cancellation_hides_later_failure_without_loop_error` (:19), `test_sqlite_session_post_commit_cancellation_propagates_after_known_outcome` (:1150).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "await mutation cancellation sqlite write connection invalidate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any fire-and-forget persistence under asyncio where losing the outcome is worse than surfacing cancellation late; adapt storage backend freely — the pattern is backend-agnostic.
