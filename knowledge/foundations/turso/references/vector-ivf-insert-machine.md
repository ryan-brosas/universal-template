<!-- capsule-v2 -->
# Vector-IVF insert machine — how does one sparse vector become posting rows + stats, and why is the inverted seek's result thrown away?

**Source:** turso (MIT) `main@1654d1587fab` ($REFERENCE_ROOT/turso); Codebase Memory `turso`. **Question:** What exact per-component write ladder turns `INSERT INTO t(vector32_sparse(...))` into index content, and which error checks are deliberately skipped?

## Six-state resume machine; one posting row per (position, sum, rowid); blind insert
**Path/Symbol:** `core/index_method/toy_vector_sparse_ivf.rs`: `VectorSparseInvertedIndexInsertState` enum (:45-87), `insert` (:531-783), `parse_stat_row` (:162-194).
**Signature:** `fn insert(&mut self, values: &[Register]) -> Result<IOResult<()>>` with `values = [sparse_vector_blob, rowid_i64]`.
**Data Shape:** posting row key = `(position i64, sum f64, rowid i64)` where **`sum` = Σ of the vector's values, computed once in Init (:562) and copied into EVERY posting row**. Stats row = `(position, cnt i64, min f64, max f64)`.

### Decisive source
```rust
// toy_vector_sparse_ivf.rs:608-631 + :645 — seek result DISCARDED, then unconditional insert:
VectorSparseInvertedIndexInsertState::SeekInverted { .. } => {
    let result = return_if_io!(inverted_cursor.seek(
        SeekKey::IndexKey(k.as_record_ref()),
        SeekOp::GE { eq_only: true }
    ));
    tracing::debug!("insert_state: seek: result={:?}", result);
    self.insert_state = VectorSparseInvertedIndexInsertState::InsertInverted { .. };
}
// InsertInverted arm:
return_if_io!(inverted_cursor.insert(&BTreeKey::IndexKey(k.as_record_ref())));
```

**Flow:** Init validates Float32Sparse blob + rowid, computes `sum` → Prepare loops per component `idx`: exhausted ⇒ reset to Init and Done → build 3-col key → SeekInverted (result ignored) → InsertInverted → SeekStats on `(position)`: Found ⇒ ReadStats merges `cnt+1`, `value.min(min)`, `value.max(max)` (:721-759); NotFound|TryAdvance ⇒ fresh row `(1, value, value)` (:687-718) → UpdateStats inserts the stats row and returns to Prepare with `idx+1`.
**Invariant:** the state payload (`vector: Option<Vector>`, `sum`, `rowid`, `idx`, `key`) rides ON the enum variant across every IO yield — the same resume discipline as the vdbe opcode machines — so a mid-vector yield can resume without re-parsing registers. The blind insert is sound because a duplicate `(position,sum,rowid)` key overwrite is idempotent for the SAME row content; delete (its paranoid twin) is what detects real corruption.
**Probe:** executed at HEAD: `test_vector_sparse_ivf_insert_query` (tests/integration/index_method/mod.rs:153-241) drives raw-cursor insert of four unit vectors then asserts exact distances (`[1,0,0,1]` ⇒ rows 1&4 at distance 0.5; `[1,1,1,1]` ⇒ all at 0.75). Grep anchors verified byte-exact: `SeekResult::NotFound | SeekResult::TryAdvance` insert-stats arm = :687.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "VectorSparseInvertedIndexInsertState insert", limit: 10 });
```
resolves the enum :45-87 and `insert` :531-783 line-exact.

## Verdict
Adopt the per-component two-write ladder (posting row + cnt/min/max merge) and the state-on-variant resume shape. Adopt "sum denormalized into every posting row" only together with the query-side threshold consumer that justifies it. Adapt validation: turso repeats the Float32Sparse check at each register boundary rather than factoring it. Omit the debug-tracing noise. Coverage: no_recorded_issue.
