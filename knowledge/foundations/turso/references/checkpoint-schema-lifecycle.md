<!-- capsule-v2 -->
# Checkpoint schema lifecycle — how does checkpoint turn sqlite_schema row versions into B-tree create/destroy ops without corrupting a reused root page?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** When materializing schema history, how do you decide which sqlite_schema version means CREATE, which means DROP, and which is just a metadata rewrite of a live object?

## B-tree identity extraction + drop-ts binding resolution
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs` — `sqlite_schema_btree_identity` (:407-450), `sqlite_schema_versions_refer_to_btree` (:452-456), `is_schema_metadata_only_rewrite` (:458-479), `resolve_dropped_binding` (:1049-1069), collection dispatch (:1157-1282), `SpecialWrite` enum (:371-393).
**Signature:** `fn sqlite_schema_btree_identity(version: &RowVersion) -> Option<SqliteSchemaBtreeIdentity>` → `{kind: Table|Index, root_page: i64}`; `fn resolve_dropped_binding(&self, root_page: u64, version: &RowVersion) -> Option<MVTableId>`.
**Data Shape:** identity decodes record cols 0 (`type`) and 3 (`rootpage`) via `ImmutableRecordRef::get_two_values(0, 3)`; payload-less tombstones (recovery-synthesized) return None — "Recovery never replays a sqlite_schema delete as an empty payload" intent annotation :410-414; root_page==0 (views/triggers) returns None.

### Decisive source
```rust
// :1050-1055 — WHY covering-window lookup, not "any live binding at this root":
// "Selects the binding that COVERS the drop timestamp (`begin < drop_ts <= end`)
//  rather than \"any live binding at this root\": under concurrent page reuse a
//  freed root page can already belong to a newer live object, and destroying
//  that one would corrupt a live btree."
// :458-465 — WHY same-object rewrites collapse:
// "Some of those transitions are metadata-only rewrites of the same B-tree
//  object… Same-object rewrites, such as `ALTER TABLE ... RENAME COLUMN`, must
//  collapse to the latest version; otherwise checkpoint treats one schema row
//  chain as a DROP+CREATE pair and emits duplicate work for the same rowid."
```

**Flow:** decode identity → non-schema rows skip this path → CREATE (root<0, uncheckpointed sentinel): emit `SpecialWrite::BTreeCreate{Index}` keyed by sqlite_schema rowid → DROP of never-checkpointed object (root<0 on a tombstone): register destroyed-set only, no physical destroy → DROP of checkpointed object (root>0): resolve owning binding AT the drop ts, then `BTreeDestroy{Index}` → same-object rewrite (identity equal): collapse, plain row write, no special write → no successor: treat ended version as real drop (`is_schema_metadata_only_rewrite(current, None) == true`).
**Invariant:** a physical `btree_destroy` may fire ONLY for the binding whose `[begin, end]` window covers the drop timestamp; identity equality (kind + root_page) is the sole evidence that two versions are the same object, so RENAME must not mint create/destroy pairs.
**Probe:** `checkpoint_state_machine.rs::tests::sqlite_schema_identity_treats_index_sql_rewrite_as_same_object` (:3282), `sqlite_schema_identity_detects_drop_recreate_as_different_objects` (:3307), `sqlite_schema_identity_ignores_payloadless_tombstones` (:3340); integration `test_create_rename_insert_same_tx_recover_then_checkpoint` (tests/integration/mvcc.rs:1096).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "sqlite_schema_btree_identity resolve_dropped_binding", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the identity-decode + covering-window resolution pair verbatim for any versioned-catalog materializer; adapt the col0/col3 positions to your catalog layout; omit payloadless-tombstone tolerance if your recovery always preserves payloads. Coverage caveat: none material — probes are direct tests in-file.
