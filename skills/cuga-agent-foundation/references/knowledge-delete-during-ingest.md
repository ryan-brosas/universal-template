<!-- capsule-v2 -->
# Delete-vs-ingest resurrection guard — how do you delete a file while its ingest is running and guarantee the delete is not silently undone?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (#691/#692/#697); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Delete used to ignore active ingests entirely — the button did nothing on first upload (no documents row yet → 404 while ingest carried on) and resurrected deleted content on re-upload. What is the correct interleaving?

## _stop_ingest_for + bounded wait + retryable refusal
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:3087-3135` (`_stop_ingest_for`), `:3146-3175` (`delete_document` call-site ordering), `routes.py:809-812` (`IngestStillFinishingError → HTTP 409`).
**Signature:** `async _stop_ingest_for(collection, filename) -> bool`; raises `IngestStillFinishingError(filename, task_id)`.

### Decisive source
```python
# engine.py:3087-3135 — stop, wait bounded, REFUSE rather than lie
        for task in await self._metadata.list_tasks(collection):
            if not self._blocks_reupload(task, filename):
                continue
            await self.cancel_task(task["task_id"])
            stopped = True
            deadline = time.monotonic() + _DELETE_INGEST_WAIT_S
            while time.monotonic() < deadline:
                current = await self._metadata.get_task(task_id)
                if not current or current.get("status") in ("completed", "failed", "cancelled"):
                    break
                await asyncio.sleep(0.1)
            else:
                # Do NOT delete anyway. That worker is past the point of no
                # return, so it still has an add_document ahead of it: deleting
                # now would report success and then be silently undone by that
                # write — reintroducing the exact resurrection this method
                # exists to prevent, just in the timeout window. Fail
                # retryably instead of lying about the outcome.
                raise IngestStillFinishingError(filename, task_id)
```
```python
# engine.py:3153-3171 — ordering IS the deadlock avoidance
        # Outside the lock on purpose — see _stop_ingest_for.
        stopped_ingest = await self._stop_ingest_for(collection, filename)
        async with self._get_collection_lock(collection):
            ...
            if not await self._metadata.mark_deleting(collection, filename):
                if stopped_ingest:
                    # No documents row because the ingest never indexed — but we
                    # DID stop it, so user intent is satisfied. 404 here would be
                    # a lie about work we actually did.
                    logger.info(f"Delete {filename}: ingest stopped before it indexed anything")
                    return
                raise DocumentNotFoundError(filename)
```

**Flow:** cancel first (which respects the point of no return from knowledge-cancel-point-of-no-return), then poll every 0.1s up to 30s for a terminal status; only after the ingest is terminal does the delete take the collection lock and proceed — so the delete runs LAST instead of being overwritten by a still-in-flight `add_document`. The 30s bound exists so a wedged provider call cannot hang the HTTP request; on expiry the route maps `IngestStillFinishingError` to 409 with "retry the delete shortly" semantics because the ingest WILL still write.

**Invariant:** (1) `_stop_ingest_for` must run BEFORE taking the collection lock — waiting on the worker while holding it deadlocks, since the worker needs that same lock to insert. (2) A delete that stops a pre-index ingest returns SUCCESS even though `mark_deleting` finds no row: honest-intent semantics beat literal 404. (3) Timeout NEVER falls through to delete-anyway — that trades a truthful 409 for a lie that gets undone. (4) Reindex-busy rejection still wins over delete (checked both outside and re-checked under the lock for TOCTOU closure).

**Probe:** direct tests `tests/unit/test_knowledge_delete_during_ingest.py::test_delete_during_first_upload_stops_the_ingest` (:85), `::test_delete_during_reupload_is_not_resurrected` (:113), `::test_delete_with_no_document_and_no_ingest_still_404s` (:143), `::test_delete_refuses_rather_than_lying_when_the_ingest_outlives_the_deadline` (:164, monkeypatched deadline), `tests/unit/test_knowledge_routes.py` route mapping assertions; `tests/unit/test_knowledge_delete_during_ingest.py::test_delete_route_maps_ingest_still_finishing_to_409` (:215).

## Get live surrounding code
**Retrieve:**
```ts
mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_stop_ingest_for IngestStillFinishingError delete_document mark_deleting", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** ADOPT for any mutating request that races a long-running writer with commit phases: cancel → bounded poll → refuse-retryable on expiry → proceed only once the writer is provably terminal, all OUTSIDE the writer's own lock.
