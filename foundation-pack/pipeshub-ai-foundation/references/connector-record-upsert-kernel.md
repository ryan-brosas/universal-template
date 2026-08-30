<!-- capsule-v2 -->
# Record upsert kernel — what exactly happens when a connector re-sends an existing record: version bumps, indexing-status machine, null-carry-forward?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** The single most re-implemented loop in any sync engine: how does re-delivery of a record decide version++, status reset vs preservation, and field backfill — without re-embedding unchanged content?

## Version-fill ladder + COMPLETED-sticky status machine
**Path/Symbol:** `backend/python/app/connectors/core/base/data_processor/data_source_entities_processor.py:` `_process_record` (:954-1087), `_mark_queued_after_publish` (:1089-1110).
**Signature:** `async def _process_record(record: Record, permissions: list[Permission], tx_store: TransactionStore) -> Record | None`; lookup via `tx_store.get_record_by_external_id(connector_id, external_record_id)`.
**Data Shape:** Record carries `version` (int, default 0), `external_revision_id` (vendor etag/updatedAt), `indexing_status` ∈ ProgressStatus{NOT_STARTED, QUEUED, IN_PROGRESS, COMPLETED, AUTO_INDEX_OFF,...}, `is_placeholder`, optional `weburl/source_created_at/source_updated_at`.

### Decisive source
```python
if record.version == 0:
    if record.is_placeholder:
        record.version = existing_record.version            # stubs never bump
    elif existing_record.is_placeholder:
        record.version = 0                                   # stub→real IS first version
    else:
        record.version = existing_record.version + (
            1 if record.external_revision_id != existing_record.external_revision_id else 0)
...
if record.indexing_status != ProgressStatus.AUTO_INDEX_OFF.value:
    record.indexing_status = ProgressStatus.NOT_STARTED.value   # real change requeues
else:
    # Unchanged content stays COMPLETED (blocks re-publish below). Resetting
    # unconditionally made every full re-sync re-embed the entire already-indexed set,
    # and clobbered AUTO_INDEX_OFF on manually-indexed records.
    record.indexing_status = ProgressStatus.COMPLETED.value
...
if record.source_created_at is None:
    record.source_created_at = existing_record.source_created_at
    # Neo4j upsert is `SET n +=`: a null-valued key DELETES the stored property —
    # without this carry-forward every re-sync silently erased backfilled dates.
```

**Flow:** fetch existing by external id → fill org_id ONLY if unset (KB/cross-org callers win) → resolve record_group BEFORE first save → new? full insert path : run ladder above → revision changed ⇒ `_handle_updated_record`; group-link AFTER save (needs record.id for edges) → KB uploads anchor `belongsTo` app + PARENT_CHILD to parent folder; connectors go through `_handle_parent_record` (+ placeholder-parent synthesis) → related-external-record edges ALWAYS rebuilt for ticket/project/sql records (cleans stale links even when list empty) → permission edges → publish events, THEN compare-and-set NOT_STARTED→QUEUED (CAS loses cleanly if indexing already progressed — losing is correct, not error).
**Invariant:** (1) version bumps ONLY on real content delta, never for placeholders or metadata refreshes; (2) AUTO_INDEX_OFF is sticky across content changes — manual indexing choice outranks freshness; (3) every nullable vendor field must be carried forward or the graph store erases it on merge; (4) QUEUED promotion strictly AFTER publish, as a CAS that prefers the racing consumer.
**Probe:** `grep -c 'external_revision_id !=' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `3`; `grep -c 'AUTO_INDEX_OFF' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `10`; suites `tests/unit/connectors/core/test_data_processor.py` (128) + `test_data_source_entities_processor.py` (244 tests) — e.g. `:381 test_existing_record_with_new_revision`, `:519 test_unchanged_completed_record_publishes_nothing`, `:545 test_content_change_does_not_override_manual_indexing` — ALL GREEN in the executed battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "DataSourceEntitiesProcessor _process_record record version", limit: 3 });
```
(rank #1 `_process_record` :954-1087.)
**Verdict:** Adopt whole (ladder + status machine + carry-forward + post-publish CAS); adapt Record dataclass/ProgressStatus enum to host; omit Arango/Neo4j provider specifics behind the TransactionStore interface.
