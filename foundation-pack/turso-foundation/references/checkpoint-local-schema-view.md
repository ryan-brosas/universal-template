<!-- capsule-v2 -->
# Snapshot-consistent schema view — why must a passive checkpoint read the on-disk sqlite_schema instead of trusting the live schema, and how is the snapshot rebuilt?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How do you build a schema view that matches exactly what your version collection sees when concurrent DDL can commit mid-checkpoint?

## BuildLocalSchemaViewStateMachine: disk scan + MVCC delta overlay at snapshot_ts
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs` — `BuildLocalSchemaViewState` (:3048-3059), machine (:3061-3222), `merge_mvcc_delta` (:3092-3144), passive wiring in `step_inner::BuildLocalSchemaView` (:2013-2079), snapshot-keyed index map (:2050-2069).
**Signature:** states `Rewind → ReadRowid → ReadRecord{rowid} → Advance → MergeMvccDelta → Done`; result `Arc<Schema>` via `mvstore.build_schema_from_rows(&connection, &rows, &[])`.
**Data Shape:** `rows: HashMap<i64, ImmutableRecordRef<'static>>` keyed by sqlite_schema rowid; disk rows cloned out of the B-tree (root page 1), then overwritten/removed by the MVCC overlay; overlay keeps the version with `begin <= ts < end-or-open`, and removes a rowid whose live-at-snapshot state is a delete.

### Decisive source
```text
// :3048-3051 — the reason the live schema cannot be used:
// "scans the on-disk `sqlite_schema` B-tree (root page 1) and overlays the
//  MVCC delta visible at `snapshot_ts`, matching exactly the rows the
//  checkpoint collects. The live schema would include post-snapshot objects
//  and mis-map index ids."
// :2055-2060 — index ids must resolve AT the snapshot too:
// "Key each index by the binding that owns its root page AT snapshot_ts —
//  the same id collect_index_rows uses… Resolving at the *current* owner
//  (u64::MAX) instead would, under concurrent page reuse, key a present
//  index under a different (reused) id, so WriteIndexRow would fail to find
//  its Index struct and drop real entries (\"row N missing from index\")."
```

**Flow:** (passive only) optionally begin a pager read tx if the WAL read lock isn't already held (`build_local_schema_began_read_tx`) → cursor scan of root page 1 collecting rowid→record → overlay MVCC sqlite_schema versions live at `snapshot_ts` (insert present payloads, remove dropped rowids) → build Schema from merged rows → re-derive `index_id_to_index` via `try_get_table_id_from_root_page_at(root, snapshot_ts)` → end the read tx it began.
**Invariant:** every id the write phase resolves (index structs, roots) must come from state as of `snapshot_ts` — mixing current-owner lookups into a snapshot collection silently drops or corrupts entries under root-page reuse; the sub-machine owns its own read-tx lifecycle so the outer checkpoint never double-begins.
**Probe:** `checkpoint_state_machine.rs::tests::local_schema_record_shares_mvcc_payload` (:3270) pins the zero-copy payload sharing; behavioral pinning of drop-during-collection lives in tests/integration/mvcc.rs checkpoint-recovery suite (`test_create_insert_drop_checkpoint_recover` :997).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "BuildLocalSchemaViewStateMachine merge_mvcc_delta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scan+overlay for any materializer whose catalog and data versions advance concurrently; adapt the overlay predicate to your visibility rule; omit entirely if you checkpoint under a stop-the-world lock (the blocking path does). Coverage caveat: identity probes are direct unit tests; full-view behavior is pinned by integration recovery tests.
