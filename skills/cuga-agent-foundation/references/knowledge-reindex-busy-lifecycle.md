<!-- capsule-v2 -->
# Reindex busy-flag lifecycle — how do you close the delete/reindex TOCTOU and guarantee a wedged worker can never pin a collection forever?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What stops a concurrent delete from resurrecting a document during reindex, and what self-heals when an embedding call hangs for 30 minutes?

## Flag-under-lock + snapshot + terminalize-on-timeout
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:4311-4436` (`reindex`), worker timeout constant `_REINDEX_WORKER_TIMEOUT_S = 1800` at `:47-52`; delete-side double guard `:2929-2967` (`delete_document` fast-path + in-lock recheck); weak-ref task set `_BACKGROUND_REINDEX_TASKS` at `:54-57`.
**Signature:** `async def reindex(collection: str) -> dict` raising `ReindexBusyError(pending_count)` (`:762-767`) when pending/running tasks exist; sets `_reindex_in_progress.add(collection)` under `_get_collection_lock`.
**Data Shape:** `_reindex_in_progress: set[str]` of collection names; file list snapshot taken AFTER flagging, under the SAME lock; background worker = `asyncio.gather(..., return_exceptions=True)` wrapped in `asyncio.wait_for(timeout=1800)`.

### Decisive source
```python
# engine.py:4330-4341 — flag and snapshot atomically under the collection lock
lock = self._get_collection_lock(collection)
async with lock:
    pending = [t for t in await self._metadata.list_tasks(collection)
               if t["status"] in ("pending", "running")]
    if pending:
        raise ReindexBusyError(len(pending))
    self._reindex_in_progress.add(collection)
    # Snapshot the file list AFTER flagging, under the same lock, so a
    # concurrent delete either ran before the flag (and is excluded)
    # or is rejected by delete_document's in-lock re-check — closing
    # the delete/reindex TOCTOU that could resurrect a deleted doc (CR-D).
    file_list = [f for f in files_dir.iterdir() if f.is_file()]
```
The TOCTOU closes because BOTH sides take the same per-collection lock: `reindex` flags+snapshots inside it; `delete_document` fast-path-rejects on the flag, then RE-CHECKS the flag under the same lock before marking deleting (`:2950-2960`). A delete that slips the fast path is still caught before it can race the snapshot.

**Flow:** reindex → under lock: refuse if tasks active → set flag → snapshot files → drop vectors (still under lock) → spawn per-file `_run_ingest` workers concurrently (bounded by `_ingest_sem`) → worker `finally` discards flag. Timeout self-heal (`:4368-4409`): `wait_for` fires ⇒ log "wedged provider call?" ⇒ terminalize every still-pending/running task row as `status="failed"` with `error="reindex timeout"` — WITHOUT this the next reindex would see zombie rows and raise ReindexBusyError forever, so the timeout wouldn't actually heal. `finally` also discards `_reindex_deferred`. Two supporting quirks: workers are pinned via module-level strong-ref set with done-callbacks (the event loop keeps only WEAK refs to bare `create_task()` results; GC mid-run would drop the finally that clears the busy flag), plus `add_done_callback(lambda t: t.exception())` so a crashed worker logs instead of vanishing.

**Invariant:** A collection flagged `_reindex_in_progress` admits no uploads, no deletes (both raise `ReindexInProgressError`, mapped to 409 at the route layer), and no vector-affecting config apply until the flag clears; every path that spawns the worker must have a `finally` that clears it, and every wait on workers needs a wall-clock cap.
**Probe:** `tests/unit/test_knowledge_reindex_in_progress_guard.py:121-146` (delete rejected during reindex / allowed when idle), `:148-184` (vector change rejected BEFORE preflight); semaphore bound pinned separately by `tests/unit/test_knowledge_ingest_concurrency.py:25-49` (peak == max_ingest_workers exactly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "reindex _reindex_in_progress ReindexInProgressError delete_document collection lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flag+snapshot under one lock with mirrored guards on the mutating operations, the 30-minute terminalize-on-timeout self-heal, and strong-ref pinning of fire-and-forget tasks. Adapt the timeout value and status vocabulary. Omit the CR-D issue-history references.
