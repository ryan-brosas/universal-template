<!-- capsule-v2 -->
# Vacuum target-build engine — how do you rebuild a compacted database image by replaying schema and copying rows through ordinary SQL statements inside one transaction?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** In what order are tables, data, indexes, and triggers/views recreated — and which entries must be excluded from creation yet still copied?

## Phase classification + 13-phase async machine
**Path/Symbol:** `core/vdbe/vacuum.rs:classify_schema_entries` (:110-181), `VacuumTargetBuildPhase` (:481-526), `vacuum_target_build_step` (:547-1031).
**Signature:** `fn classify_schema_entries(entries: &[SchemaEntry]) -> (Vec<usize> /*create*/, Vec<usize> /*copy*/, Vec<usize> /*indexes*/, Vec<usize> /*post-data*/)`.
**Data Shape:** `SchemaEntry { entry_type, name, tbl_name, rootpage: i64, sql }` parsed from sqlite_schema `(type,name,tbl_name,rootpage,sql) ORDER BY rowid`; storage-backed = `rootpage != 0` — "MVCC can use NEGATIVE rootpage values before checkpointing, so this checks `!= 0` rather than `> 0`" (:71-76).

### Decisive source (the exclusion that breaks naive ports)
```rust
// :121-141 — sqlite_sequence AND autoincrement backing tables:
//   skipped for CREATE replay, kept for COPY
// User-created sequence backing tables (`CREATE SEQUENCE foo` →
// `__turso_internal_seq_foo`) DO need creation replay — that backing
// table IS the persistent representation of the sequence ... Excluding
// them used to abort VACUUM with `no such table` during the copy phase.
if !entry.is_sqlite_sequence() && !entry.is_autoinc_sequence_backing_table() {
    tables_to_create.push(idx);
}
tables_to_copy.push(idx);   // ALL storage-backed tables incl. sqlite_stat1
```

**Flow:** Init mirrors symbols/functions/vtab/index-methods + custom types into the target, installs auto-vacuum mode BEFORE MVCC bootstrap ("otherwise full auto-vacuum can reserve page 2 as a ptrmap page after MVCC has already used it as a root" :567-574), sets perf flags (sync OFF, FK off, check-constraints ignored, auto-checkpoint off — SQLite vacuum.c parity), wraps everything in ONE `BEGIN IMMEDIATE`, optionally excludes the MVCC meta table from replay (VACUUM INTO excludes: destination bootstraps it; in-place includes: temp image becomes THE physical source, :597-615) → CollectSchemaRows → per-table CREATE (system tables prepared under a temporary `start_nested()` guard ONLY around prepare — "keeping it during step() would make this CREATE TABLE look nested, so its Transaction opcode would skip write setup" :692-701) → row copy via `SELECT/INSERT` pairs with columns derived from `BTreeTable.columns` NOT `PRAGMA table_info` ("table_info omits generated columns while SELECT * includes them - causing a column count mismatch" :743-746); virtual generated columns filtered both sides; rowid preservation picks the first unshadowed alias of `rowid/_rowid_/oid` and EXCLUDES an INTEGER PRIMARY KEY alias column from the data list since it IS the rowid (:1094-1157); `INSERT OR REPLACE` only for sequence/autoinc backing tables (stale auto-counters overwritten) → CREATE INDEX after data (backing-btree indexes of custom index methods filtered out — recreated by their parent CREATE in post-data) → triggers/views/rootpage=0 LAST so triggers cannot fire during copy → FinalizeTargetHeader (schema_cookie+1) → COMMIT.

**Invariant:** The four-phase ordering is correctness, not style: create-before-copy satisfies FK-less bulk insert; indexes-after-data avoids incremental maintenance; post-data-last prevents trigger firing during copy. Every exclusion pair (sequence: no-create/yes-copy; backing-btree: no-index-create/parent-recreates) exists because exactly one producer owns each object.
**Probe:** `grep -n 'fn vacuum_target_build_preserves_nested_statement_explicit_yield\|fn capture_target_metadata_uses_final_header_cookie_and_preserves_tvfs\|fn internal_vacuum_temp_db_uses_source_runtime_and_disables_auto_checkpoint' core/vdbe/vacuum.rs` → hits in the same-file test module; runnable `cargo test --features conn_raw_api -p turso_core --lib vacuum_target_build`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "classify_schema_entries build_copy_sql VacuumTargetBuildContext mirror_symbols", limit: 8 });
// resolves SchemaEntry/classify plane + copy-SQL builder (build_copy_sql :1055-1181)
```

## Verdict
Adopt phase-ordered replay through ordinary statement execution, rootpage≠0 storage test (negative roots!), exclusion taxonomy, nested-guard-only-at-prepare, and BTreeTable-derived column lists. Adapt dialect replay hooks (`table_sql_for_replay`). Omit wasm stub. Coverage: graph Retrieve resolves the classification/copy seams; direct tests in same file module.
