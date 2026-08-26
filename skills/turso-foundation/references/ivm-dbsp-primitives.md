<!-- capsule-v2 -->
# DBSP primitives — why are Z-set keys full rows, and how are operators identified in storage?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** What row identity, hashing, and storage-id encoding must an IVM porter copy from the DBSP layer?

## Hash128 / HashableRow / Delta / generate_storage_id
**Path/Symbol:** `core/incremental/dbsp.rs` Hash128 (:19), HashableRow (:141, was :150 at `main@d9266124f`) with the 82/88-hours design comment (:127, was :122-136), Delta (:202, was :209); `core/incremental/operator.rs:generate_storage_id` (:65), `IncrementalOperator::{eval,commit}` trait (:219-241 region), `create_dbsp_state_index` (:44).
**Signature:** `pub fn generate_storage_id(operator_id: i64, column_index: usize, op_type: u8) -> i64`; `pub fn hash_values(values: &[Value]) -> Self` (Hash128).
**Data Shape:** `Delta { changes: Vec<(HashableRow, isize)> }` — ORDERED, weight +1 insert / −1 delete. `HashableRow { rowid: i64, values: Vec<Value>, cached_hash: Hash128 }` (hash precomputed once; rows are immutable and rehashed constantly during joins).

### Decisive source
```rust
// core/incremental/dbsp.rs — THE porting lesson, verbatim rationale
// Empirically speaking, using row keys as the ZSet keys will waste a competent but
// not brilliant engineer around 82 and 88 hours ... If the "key" is 5, then inside
// the Delta set, we will have (5, weight = -1), (5, weight = +1), and the whole
// thing just disappears. The Delta set, therefore, has to contain ((5, 5), weight = -1),
// ((5, 1), weight = +1).
```
```rust
// core/incremental/operator.rs — pack (operator, column, type) into ONE i64
assert!(op_type <= 3, "Invalid operation type");
assert!(column_index < 16384, "Column index too large");
((operator_id) << 16) | ((column_index as i64) << 2) | (op_type as i64)
```
Hash128 = UUID v5 (SHA-1, NAMESPACE_DNS) over a string form with per-type prefixes (`N:`/`I:`/`F:` bits-string/`T:`/hex `B:`) joined by NUL; floats serialized via `to_bits` for stable representation. Stored as Blob(16); low 64 bits double as synthetic rowid (`as_i64`).

**Flow:** input operators emit Deltas keyed by full-row identity → join/filter/project/aggregate operators implement `eval` (read state via `DbspStateCursors`) and `commit` (apply DeltaPair, persist operator state to the 5-column b-tree addressed by generate_storage_id) → outputs feed downstream nodes or the view write-back.
**Invariant:** Z-set keys are FULL records (rowid+values) — keying by primary key silently swallows updates that cross predicate boundaries; consolidation happens only at explicit `consolidate()` so ordering of delete-before-insert survives until merge.
**Probe:** `core/incremental/dbsp.rs::test_hashable_row_delta_operations` (:498, start unchanged at `main@d9266124f` — update captured as 3 ops [insert,delete,insert], consolidate leaves exactly the final insert) and `test_zset_merge_with_weights` (:461). Text anchors: `grep -c '82 and 88 hours' core/incremental/dbsp.rs` → 1; `grep -c '((operator_id) << 16)' core/incremental/operator.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "HashableRow Delta generate_storage_id IncrementalOperator", limit: 10 });
```

## Verdict
Adopt full-row Z-set keys, ordered deltas with deferred consolidation, deterministic SHA-1 hashing, and the bit-packed storage id (keep the ≤3 type / <16384 column asserts). Adapt UUID dependency to any 128-bit hash. Omit ComputationTracker stats plumbing.
