<!-- capsule-v2 -->
# Replace-duplicates dedup + schema-mismatch self-heal — how do you re-ingest a file without dupes, and what do you do when the vector backend's schema disagrees mid-flight?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Where must delete-by-source and record-manager cleanup run relative to insert, and how does a `DataNotMatch`/schema error recover without losing the ingest?

## Pre-delete both stores → single add; on schema mismatch drop + recreate + retry ONCE
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:2794-2866` (`_insert_documents_async`), metadata-normalization that prevents most mismatches `:2553-2598` (keep only `source`/`filename`/`page`/`section_path`, coerce non-primitives to str), chunk-limit truncation `:2545-2549`.
**Signature:** `_insert_documents_async(collection, docs, source_id, filename, replace_duplicates, retry=True, stage_timings=None, progress_cb=None) -> dict{num_added,num_skipped,num_updated}`; runs the mutation via `asyncio.to_thread(_vector_mutation)` under `_vector_store_lock`.
**Data Shape:** `source_id = f"{collection}/{filename}"` is the join key across THREE stores: vector adapter (`delete_by_source`), `InMemoryRecordManager` (`delete_keys([source_id])`), and metadata DB (`document_exists`). `section_path` is a FLAT string (D1) — nested arrays trip cross-format metadata schema conflicts.

### Decisive source
```python
# engine.py:2802-2827 — the serialized critical section
def _vector_mutation() -> dict:
    with self._vector_store_lock:
        adapter = self._vector_stores[collection]
        if replace_duplicates and doc_exists:
            try:
                adapter.delete_by_source(source_id)
            except Exception as e:
                logger.debug(f"Pre-delete for {source_id}: {e}")
            rm = self._record_managers.get(collection)
            if rm:
                try:
                    rm.delete_keys([source_id])
                except Exception:
                    pass
            return adapter.add_documents(docs, **common_kwargs)
        if not doc_exists:
            return adapter.add_documents(docs, **common_kwargs)
        return {"num_added": 0, "num_skipped": len(docs)}
```
Schema-mismatch recovery (`:2840-2866`): if the insert raises with `DataNotMatch` or `schema` in the message AND `retry=True` — pop the cached adapter AND record manager, rebuild the store, DROP its vectors, wipe collection metadata, then recurse ONCE with `retry=False` (no infinite loop). The normalization pass earlier in `_ingest_inner` is the prevention half of this seam: only JSON-friendly primitive fields ride on chunks, exotic types are coerced to str with a warning, pages that fail int() become absent rather than dirty.

**Flow:** caller (already inside the per-collection lock from `_ingest_inner`) → check doc_exists in metadata → under `_vector_store_lock`: replace-mode ⇒ pre-delete vectors + record-manager keys (both best-effort) then single bulk `add_documents`; new-doc ⇒ plain insert; duplicate-not-replacing ⇒ skip all. Failure classified as schema ⇒ nuke collection state and replay once.
**Invariant:** Dedup correctness requires the whole check-delete-insert sequence to be serialized per collection (the lock taken in `_ingest_inner`) — parse may run concurrently, mutation may not. Record-manager keys MUST be cleaned alongside vectors or the next upsert misjudges freshness. Self-heal recursion must be bounded (retry=False) or a persistent schema conflict loops forever.
**Probe:** No dedicated unit test for the DataNotMatch path (needs a misbehaving backend stub) — coverage caveat recorded. Adjacent pins: `tests/unit/test_knowledge_progress.py` (add_documents callback contract per sub-batch), `tests/unit/test_knowledge_engine.py:61` (`get_deleting_documents` for the compensating-delete flow).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_insert_documents_async delete_by_source InMemoryRecordManager DataNotMatch schema recreate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt source-keyed pre-delete across vector+record stores inside one serialized section, flat-string metadata discipline to avoid schema conflicts, and the bounded drop-recreate-retry-once self-heal. Adapt the error-matching substrings to your backend's vocabulary. Omit stage-timing plumbing freely.
