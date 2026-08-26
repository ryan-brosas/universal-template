<!-- capsule-v2 -->
# Batch operation accounting — How do add/update/delete counts net out when one ID is mutated repeatedly within a batch?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** A batch models "a set of changes as an atomic operation" — what are the exact counter rules a porter must replicate so k-clamping and label allocation stay correct?

## Batch.apply
**Path/Symbol:** `chromadb/segment/impl/vector/batch.py:Batch.apply` (:53-106).
**Signature:** `apply(self, record: LogRecord, exists_already: bool = False) -> None`; state = `_ids_to_records`, `_written_ids: Set`, `_deleted_ids: Set`, `_upsert_add_ids: Set`, public `add_count`/`update_count`.
**Data Shape:** One record per ID (`_ids_to_records[id]` overwritten on re-write); DELETE removes from `_ids_to_records` entirely; counters are derived invariants, not independent state.

### Decisive source
```python
if record["record"]["operation"] == Operation.DELETE:
    if id in self._written_ids:
        self._written_ids.remove(id)
        if self._ids_to_records[id]["record"]["operation"] == Operation.ADD:
            self.add_count -= 1
        elif ... == Operation.UPDATE:
            self.update_count -= 1
            self._deleted_ids.add(id)
        elif ... == Operation.UPSERT:
            if id in self._upsert_add_ids:
                self.add_count -= 1
                self._upsert_add_ids.remove(id)
            else:
                self.update_count -= 1
                self._deleted_ids.add(id)
    elif id not in self._deleted_ids:
        self._deleted_ids.add(id)
    if id in self._ids_to_records:
        del self._ids_to_records[id]
```

**Flow (live-verified):** UPSERT-add then DELETE nets to **zero counts and no tombstone** (the ID never existed durably, nothing downstream needs hiding); UPDATE/UPSERT-update then DELETE decrements the counter AND leaves a tombstone (the persisted index still holds the old vector until compaction). On writes, a pending delete is revoked first (`_deleted_ids.remove`), then UPSERT splits by the caller-supplied `exists_already` flag into add vs update.
**Invariant:** `add_count + update_count` always equals the number of IDs whose durable existence changed; delete_count semantics differ by history — that difference drives hnsw_k over-query compensation, so getting it wrong silently changes recall.
**Probe:** `/tmp/chroma-p1/probe_battery.py` `batch.live_netout` (executed against real Batch class, GREEN) plus byte-exact greps `batch.netout`, `batch.upd_tombstone`. Upstream direct tests: `chromadb/test/segment/impl/vector/test_local_hnsw.py` batch scenarios.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "Batch apply upsert_add_ids deleted_ids add_count", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the net-out rules verbatim — they encode which deletes need physical tombstones vs logical cancellation; adapt the exists_already flag into your own existence oracle; omit the LogRecord nesting shape (use your own record type).
