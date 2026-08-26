<!-- capsule-v2 -->
# MVCC portable delete extension — how do you express "row deleted" to an engine that cannot resolve rowids, without shipping the whole row?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** When replaying a DELETE into a foreign engine that keys rows by primary key (not your internal rowid), what must the delete op carry, and when may it carry nothing at all?

## Tombstone → PK-record reconstruction ladder with per-shape early-outs
**Path/Symbol:** `core/mvcc/database/mod.rs:732-806` (`fn portable_delete_op_extension_for_row_version`, feature `conn_raw_api`), name resolution `portable_table_name_for_mv_table_id` :705-730, encoder `LogSerializer::encode_delete_portable_extension(payload_opt, pk_record_opt, rowid)` (`persistent_storage/logical_log.rs`). Serialization call site :2365-2375 — the extension is computed inside the commit's BuildLogRecord step and passed straight into `serialize_row_version`.
**Signature:** `fn portable_delete_op_extension_for_row_version(connection, mvcc_store, row_version) -> Result<Option<Vec<u8>>>` — `None` = emit no portable bytes for this op (NOT an error).
**Data Shape:** three mutually-exclusive payload shapes by table class: sqlite_schema deletes ship `(Some(row_payload), None, Some(rowid))` — schema replay needs the full record; user-table deletes ship `(None, Some(pk_record), Some(rowid))`; pk_record = an `ImmutableRecord::from_values(&pk_values)` payload built ONLY from primary-key columns.

### Decisive source
```rust
// :738-745 — the two gates that decide "no portable bytes":
if !connection.portable_logical_changes_enabled() { return Ok(None); }
if !matches!(row_version.end(), Some(TxTimestampOrID::Timestamp(_))) { return Ok(None); }
// Only COMMITTED tombstones (end bound is a real Timestamp) become portable deletes;
// in-flight TxID-ended versions are not yet facts the outside world may learn.
// :773-782 — rowid-alias PKs are synthesized from the rowid itself:
if column.is_rowid_alias() { pk_values.push(Value::from_i64(rowid)); continue; }
```
PK reconstruction walks `table.primary_key_columns`, resolving each logical column to its PHYSICAL index before reading the decoded record (`logical_to_physical_column`) — dropping that mapping silently reads the wrong column when columns were reordered/dropped. Name resolution prefers interpreting the logged id directly as a rootpage and uses the counter-id map only as a stale-id fallback (:709-717 comment: canonical -(root_page) ids can alias unrelated counter ids).

**Flow:** portable feature off? ⇒ None. Version end ≠ committed Timestamp? ⇒ None. RowKey not Int? ⇒ None. sqlite_schema table ⇒ full-payload shape. Resolve table name (rootpage-direct first) ⇒ non-portable name ⇒ None; missing btree table ⇒ None. Else decode payload ONCE (lazily, only if a non-rowid PK column exists), extract PK values by physical index, re-encode as pk_record ⇒ extension bytes; empty extension ⇒ None.
**Invariant:** a portable DELETE must let the consumer identify the row via (pk_record | full schema payload) + rowid triple WITHOUT consulting local state; uncommitted tombstones must never leak into sync output; every early-out is `Ok(None)` — eligibility failures degrade to "not synced", never to error.
**Probe:** deterministic source pin (feature-gated code path; no standalone unit test): gates verbatim :738-745, shapes :746-755/:801-806, lazy single decode :783-794; companion codec tests beside `encode_delete_portable_extension` in logical_log.rs module tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "portable_delete_op_extension_for_row_version encode_delete_portable_extension portable_table_name_for_mv_table_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the gate-ladder + dual-shape delete encoding for any cross-engine replication of tombstones; adopt committed-only visibility as a hard filter. Adapt the PK extraction to your catalog (here: logical→physical column mapping). Omit the sqlite_schema full-payload special case if your sync protocol carries DDL out-of-band.
