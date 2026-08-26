<!-- capsule-v2 -->
# LWW merge to SQL statements — how does the Rust core merge two vaults without ever touching a database?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What is the exact conflict rule and output contract that lets one merge implementation serve browser WASM, iOS, Android, and server?

## JSON-in / SQL-out merge
**Path/Symbol:** `core/rust/src/vault_merge/mod.rs:82-150` (`merge_vaults`), :163-221 (`merge_table_by_id`), :294-333 (timestamp/key helpers).
**Signature:** `pub fn merge_vaults(input: MergeInput) -> VaultResult<MergeOutput>` where `MergeInput { local_tables: Vec<TableData>, server_tables: Vec<TableData> }`, `TableData { name: String, records: Vec<Record /* HashMap<String, serde_json::Value> */> }`, `MergeOutput { success, statements: Vec<SqlStatement { sql, params }>, stats }`.
**Data Shape:** Records are column-name→JSON maps; matching key = record `"Id"` (string); ordering key = `"UpdatedAt"` parsed as RFC3339 FIRST, then SQLite `%Y-%m-%d %H:%M:%S%.f` (:302-318) — unparseable ⇒ None ⇒ local wins silently.

### Decisive source
```rust
match (server_ts, local_ts) {
    (Some(s_ts), Some(l_ts)) if s_ts > l_ts => {
        // Server wins - generate UPDATE
        stats.conflicts += 1;
        stats.records_from_server += 1;
        if let Some(stmt) = generate_update_sql(table_name, server_record, &local_id) {
            statements.push(stmt);
        }
    }
    _ => { stats.records_from_local += 1; } // Local wins - no action needed
}
```

**Flow:** per SYNCABLE table → both sides present? compare by Id → equal timestamps or missing timestamps ⇒ LOCAL wins (strict `>` required for server) → server-newer ⇒ UPDATE all columns except Id (`WHERE Id = ?`, Id is LAST param) → server-only records ⇒ `INSERT OR REPLACE INTO <table> (...) VALUES (?...)` with SORTED columns → local-only ⇒ counted, untouched.
**Invariants:** (1) The core NEVER executes SQL — it emits ordered statements; the CLIENT applies them to its own database and re-uploads the merged blob (see client-merge-execution-plane capsule). (2) Tie goes to local; only strictly-newer server timestamps overwrite — this makes replay of the same merge idempotent. (3) Column order is sorted alphabetically so statement bytes are deterministic across runs/platforms. (4) UPDATE keeps the LOCAL Id even when server content wins (composite-key path comment "update with server data but keep local Id", :264).
**Probe:** `grep -c 's_ts > l_ts' core/rust/src/vault_merge/mod.rs` → `2` (id + composite paths); `grep -c 'INSERT OR REPLACE INTO {}' core/rust/src/vault_merge/mod.rs` → `1`; `grep -c '#\[test\]' core/rust/src/vault_merge/mod.rs` → `7`.

## Direct tests
**Path/Symbol:** in-file tests :387-500 pin local-wins-newer, server-wins-newer (UPDATE emitted), server-only insert, local-only keep, JSON FFI round-trip, and param order (`stmt.params[2] == json!("test-id")`).
**Probe:** run upstream cargo test where toolchain exists; deterministic probes above executed at pin `95903e92`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "merge_vaults", limit: 10, fields: ["signature", "name", "file"] });
```
(resolves `vault_merge.mod.merge_vaults` + wasm/uniffi twins line-exact.)

## Verdict
Adopt strict-> LWW with local-tie bias and deterministic SQL emission; adapt statement dialect to your embedded DB; omit sql.js specifics. In-file Rust tests exist but were not executed here (no cargo in inspo clone).
