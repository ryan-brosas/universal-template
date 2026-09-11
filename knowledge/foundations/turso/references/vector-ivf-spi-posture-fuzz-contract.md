<!-- capsule-v2 -->
# Vector-IVF SPI posture & fuzz contract — what is the minimal index-method posture that still gets full MVCC transactionality, and what exactly does its test promise?

**Source:** turso (MIT) `main@1654d1587fab` ($REFERENCE_ROOT/turso); Codebase Memory `turso`. **Question:** Which `IndexMethodDefinition` fields and hook overrides does a method need when it stores everything in ordinary transactional structures — and how is approximation quality pinned by tests?

## Minimal posture: no-op hooks + TransactionalBackingStore + materialized results, pinned by a differential fuzz
**Path/Symbol:** `core/index_method/toy_vector_sparse_ivf.rs`: `attach` (:321-338), `VectorSparseInvertedIndexMethodAttachment::definition` (:341-351), all five statement hooks (:513-523); contract pinned by `tests/integration/index_method/mod.rs:378-499`.
**Signature:** `fn definition<'a>(&'a self) -> IndexMethodDefinition<'a>`.
**Data Shape:** registered query patterns (:325-335) = `vector_distance_jaccard(col, ?)` AND `vector_distance_jaccard(?, col)` (both argument orders parsed as the same planned pattern).

### Decisive source
```rust
// toy_vector_sparse_ivf.rs:347-349 — the whole posture (verbatim):
backing_btree: false,
results_materialized: true,
mvcc_support: super::IndexMethodMvccSupport::TransactionalBackingStore,
// hooks :513-523: stage_statement_commit / abort_statement / on_transaction_committed /
// on_transaction_rolled_back / on_savepoint_rolled_back — ALL no-ops.
```

**Flow:** every write goes through plain btree cursor inserts/deletes inside the caller's statement transaction, so commit/rollback/savepoint semantics are inherited from the pager/MVCC planes with zero method-specific code — contrast FTS's real flush ladder (`fts-writer-slot-trigger-refusal`) and its external file manifest. `mvcc_support: TransactionalBackingStore` declares exactly this. The SQL-level proof is `test_vector_sparse_ivf_mvcc_sql` (:328-374): CREATE INDEX via `USING toy_vector_sparse_ivf`, UPDATE visible inside BEGIN, gone after ROLLBACK, correct after `PRAGMA wal_checkpoint(TRUNCATE)`.
**Invariant:** the fuzz pins BOTH sides of the delta bargain (mod.rs:464-495): result count never EXCEEDS brute force; at `delta = 0.0` rows must match brute force EXACTLY (exactness when approximation disabled); for `delta > 0` each returned distance must satisfy `brute ≤ returned ≤ brute + delta`, and every true row the scan skipped must have similarity < 1e-5 (distance ≈ 1). WITH-clause plumbing exercised at :410 (`WITH (delta = {delta})`).
**Probe:** executed at HEAD: `cargo test -p core_tester --test integration_tests -- test_vector_sparse_ivf` = **6 passed / 0 failed** (incl. `_mvcc_sql_mvcc` macro variant and `_fuzz`). Anchors verified byte-exact: posture trio :347-349; pattern pair :325-332; fuzz bound asserts mod.rs :464/:466-488.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "IndexMethodDefinition mvcc_support results_materialized backing_btree", limit: 10 });
```
resolves `definition` :341-351 plus the pass-14 SPI plane it specializes (`index-method-spi-contract`, `mvcc-index-method-write-lease`).

## Verdict
Adopt the posture matrix as the decision rule: if your method's state lives in ordinary transactional structures, no-op the five hooks and declare TransactionalBackingStore; pay real hook complexity only when state lives OUTSIDE the engine. Adopt both-argument-orders pattern registration so the planner catches either call shape. Adapt the fuzz thresholds to your engine's float determinism. Omit nothing from the differential harness — it is the only executable spec of the approximation. Coverage: no_recorded_issue.
