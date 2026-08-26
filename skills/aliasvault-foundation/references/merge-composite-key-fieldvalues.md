<!-- capsule-v2 -->
# Composite-key merge for FieldValues — why does one sync table ignore its Id column for conflict matching?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** How does the merge engine know FieldValues must match on (ItemId, FieldKey) instead of Id, and what changes in the algorithm?

## Static table registry
**Path/Symbol:** `core/rust/src/vault_merge/types.rs:33-47` (`SYNCABLE_TABLES`), :50-62 (`SYNCABLE_TABLE_NAMES`).
**Signature:** `TableConfig::new("FieldValues").with_composite_key(&["ItemId", "FieldKey"])`; all other 10 tables use plain `TableConfig::new(name)`.
**Data Shape:** `SYNCABLE_TABLES: &[TableConfig] = &[Items, FieldValues(composite), Folders, Tags, ItemTags, Attachments, TotpCodes, Passkeys, FieldDefinitions, FieldHistories, Logos]` — 11 entries; `uses_composite_key()` is `!composite_key_columns.is_empty()`.

### Decisive source
```rust
pub static SYNCABLE_TABLES: &[TableConfig] = &[
    TableConfig::new("Items"),
    TableConfig::new("FieldValues").with_composite_key(&["ItemId", "FieldKey"]),
    ...
];
```
```rust
// mod.rs:129-139 dispatch
let table_statements = if table_config.uses_composite_key() {
    merge_table_by_composite_key(table_name, local_records, server_records,
                                 table_config.composite_key_columns, &mut total_stats)
} else {
    merge_table_by_id(table_name, local_records, server_records, &mut total_stats)
};
```

**Flow:** composite path builds key by joining column values with `":"` (`get_composite_key`, :322-333; missing ⇒ empty string) → server map dedupes duplicate keys keeping the LATEST UpdatedAt (:238-246) → same strict-> LWW compare → server-wins UPDATE still targets the LOCAL row's `"Id"` while writing SERVER content ("update with server data but keep local Id", :264) → leftover server-map entries become INSERTs.
**Invariants:** (1) The registry IS the schema contract: adding a syncable table without a registry entry means it silently never merges. (2) Composite matching survives client-side regeneration of child-row Ids; Id-based matching would duplicate field values after every item rebuild. (3) The ":" join assumes Id/FieldKey values never contain ':' (UUIDs + fixed keys hold this). (4) `SYNCABLE_TABLE_NAMES` is exported separately so clients know which tables to serialize.
**Probe:** `grep -c 'with_composite_key(&\["ItemId", "FieldKey"\])' core/rust/src/vault_merge/types.rs` → `1`; `grep -c 'TableConfig::new(' core/rust/src/vault_merge/types.rs` → `11`; `grep -c 'keep local Id' core/rust/src/vault_merge/mod.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "SYNCABLE_TABLES", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the declarative per-table key config driving a single merge dispatcher; adapt to your schema diff needs; omit Rust statics. Source confirmed at pin `95903e92`; behavior covered by the 7 in-file tests (not executed here).
