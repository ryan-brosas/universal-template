<!-- capsule-v2 -->
# Vector-IVF shadow schema — how does a vector index persist without its own file format, and why does CREATE INDEX inside a statement need the subjournal opt-out?

**Source:** turso (MIT) `main@1654d1587fab` (/mnt/hdd/utopia/inspo/turso); Codebase Memory `turso`. **Question:** Where do posting lists and per-component statistics physically live so that DDL, savepoints, WAL, and checkpointing keep working unchanged?

## Two real `backing_btree` indexes named after the index method
**Path/Symbol:** `core/index_method/toy_vector_sparse_ivf.rs`: `VectorSparseInvertedIndexMethodCursor::new` (:360-395), `create` (:407-451), `destroy` (:453-478), `open_read` (:480-495), `open_write` (:497-511).
**Signature:** `fn create(&mut self, context: &IndexMethodContext) -> Result<IOResult<()>>`.
**Data Shape:** names derived once in `new`: `{index_name}_inverted_index` (:361) and `{index_name}_stats` (:362). Tunables parsed from `WITH (...)`: `delta` f64 default 0.0, `scan_portion` f64 default 1.0, `scan_order` text `"dataset_frequency_asc"|"query_weight_desc"` default QueryWeightDesc (:363-379).

### Decisive source
```rust
// toy_vector_sparse_ivf.rs:425-447 (abridged) — shadows are REAL indexes:
let inverted_index_create = format!(
    "CREATE INDEX {db_prefix}{} ON {quoted_table} USING {BACKING_BTREE_INDEX_METHOD_NAME} ({quoted_cols})",
    quote_identifier(&self.inverted_index_btree),
);
// ...
for sql in [inverted_index_create, stats_index_create] {
    let mut stmt = connection.prepare(&sql)?;
    // by default we set needs_stmt_subtransactions = true to all write transaction
    // this will lead to Busy error here - because Transaction opcode will be unable to acquire ownership to the subjournal as it already owned by parent statement which is still active
    stmt.program.prepared.needs_stmt_subtransactions.store(false, Ordering::Relaxed);
    connection.start_nested();
    let result = stmt.run_ignore_rows();
    connection.end_nested();
    result?;
}
```

**Flow:** create() emits two `CREATE INDEX ... USING backing_btree` statements on the SAME table/columns → for each: prepare → force `needs_stmt_subtransactions=false` → `start_nested()` → run → `end_nested()`. destroy() mirrors with DROP INDEX. `open_read` opens inverted cursor with **three** KeyInfo (Binary/Asc ×3 — component, sum, rowid all live in the index KEY) plus the main-table cursor; `open_write` opens only the two shadow cursors.
**Invariant:** because shadows are ordinary b-tree indexes recorded in `sqlite_master`, every lower plane already ported (btree balancing, pager savepoints, WAL framing, checkpoint schema lifecycle) applies unchanged — the method never invents storage. The subjournal opt-out is required whenever index-method DDL runs as a nested statement: the parent statement already owns the subjournal, so the child's default `needs_stmt_subtransactions=true` deadlocks into Busy (comment :435-439 calls this a hack pending proper helpers).
**Probe:** executed at HEAD: integration test `test_vector_sparse_ivf_create_destroy` asserts `schema_rows() == ["t", "t_idx_inverted_index", "t_idx_stats"]` then back to `["t"]` (tests/integration/index_method/mod.rs:134-137/:148). Runner: `cargo test -p core_tester --test integration_tests -- test_vector_sparse_ivf` = **6 passed / 0 failed** fresh compile.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "VectorSparseInvertedIndexMethodCursor create destroy open_read open_write", limit: 10 });
```
resolves `create` :407-451, `destroy` :453-478, `open_read` :480-495, `open_write` :497-511 line-exact; check_index_coverage on `core/index_method/toy_vector_sparse_ivf.rs` + `tests/integration/index_method/mod.rs` = no_recorded_issue, generation_matches=true.

## Verdict
Adopt "index method = mapping onto ordinary b-tree structures named `<index>_<role>`" — it buys transactional storage for free. Adopt the nested-DDL subjournal opt-out together with its documented caveat. Adapt naming/prefixing to your catalog conventions. Omit the `toy_` prefix semantics — nothing else is toy about the persistence story. Coverage: no_recorded_issue both cited paths.
