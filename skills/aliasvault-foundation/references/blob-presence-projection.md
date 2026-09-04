<!-- capsule-v2 -->
# Blob-presence projection — why does the pruner read `substr(Blob,1,1)` instead of the blob?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** How does a JSON-over-FFI prune avoid serializing megabytes of encrypted blobs on every run?

## substr projection queries
**Path/Symbol:** `core/rust/src/vault_pruner/mod.rs:101-121` (`get_prune_table_queries`), byte-check helper :392-401 (`value_has_bytes`).
**Signature:** `pub fn get_prune_table_queries() -> Vec<PruneTableQuery { name, query }>`.
**Data Shape:** Six SELECTs project ONLY decision columns; blob columns reduced to a 1-byte presence marker: `SELECT Id, ItemId, IsDeleted, substr(Blob, 1, 1) AS Blob FROM Attachments` and the FileData twin for Logos.

### Decisive source
```rust
/// Only the columns the pruner inspects are selected; blob columns are reduced
/// to a 1-byte presence marker (via `substr`) to avoid serializing large binary
/// data to JSON on every prune.
("Attachments", "SELECT Id, ItemId, IsDeleted, substr(Blob, 1, 1) AS Blob FROM Attachments"),
("Logos", "SELECT Id, IsDeleted, substr(FileData, 1, 1) AS FileData FROM Logos"),
```
```rust
fn value_has_bytes(value: Option<&serde_json::Value>) -> bool {
    match value {
        None => false,
        Some(serde_json::Value::Null) => false,
        Some(serde_json::Value::String(s)) => !s.is_empty(),
        Some(serde_json::Value::Array(a)) => !a.is_empty(),
        Some(serde_json::Value::Object(o)) => !o.is_empty(),
        Some(_) => true,
    }
}
```

**Flow:** client asks Rust for the query list → runs them against sql.js → rows go to JSON → pruner's Pass 3/4 use presence-only checks (`attachment_has_blob_bytes`/`logo_has_file_data_bytes`) → emitted UPDATEs clear the REAL bytes server-of-truth (`SET Blob = X''`), never the projected stub.
**Invariants:** (1) The 1-byte marker preserves emptiness semantics exactly: NULL/empty ⇒ no bytes; anything else (even the 1-char stub) ⇒ bytes present. (2) The projection is part of the FFI contract — clients MUST run these exact queries or Pass 3/4 misjudge. (3) `value_has_bytes` handles every serde_json variant because sql.js may deliver blobs as string/array/object depending on encoding.
**Probe:** `grep -c 'substr(Blob, 1, 1) AS Blob' core/rust/src/vault_pruner/mod.rs` → `1`; `grep -c 'substr(FileData, 1, 1) AS FileData' core/rust/src/vault_pruner/mod.rs` → `1`; `grep -c 'Some(serde_json::Value::' core/rust/src/vault_pruner/mod.rs` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "getPruneTableQueries", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt presence-projection over full-blob reads for any whole-table scan across FFI; adapt SQL dialect; omit the specific column names. Source confirmed at pin `95903e92`.
