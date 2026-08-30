<!-- capsule-v2 -->
# Vector-IVF exact rescore & top-K — why does the index only nominate candidates, and how do results become a stable buffered set?

**Source:** turso (MIT) `main@1654d1587fab` (/mnt/hdd/utopia/inspo/turso); Codebase Memory `turso`. **Question:** Where is the real distance computed, how is the top-K bounded, and what must hold before the first result row can be handed to the caller?

## Rescore from the live table; BTreeSet top-K with total_cmp; results fully materialized up-front
**Path/Symbol:** `core/index_method/toy_vector_sparse_ivf.rs`: `FloatOrd` (:139-152), EvaluateSeek (:1462-1525), EvaluateRead (:1526-1586), Seek-state drain (:1243-1250), `query_rowid`/`query_column`/`query_next` (:1591-1612).
**Signature:** `fn vector_f32_sparse_distance_jaccard(v1: VectorSparse<f32>, v2: VectorSparse<f32>) -> f64` (`core/vector/operations/jaccard.rs:91-125`).
**Data Shape:** candidate batch = sorted `Vec<i64>` rowids deduped through `HashSet<i64> collected`; top-K = `BTreeSet<(FloatOrd, i64)> distances`; final buffer = `search_result: VecDeque<(i64 rowid, f64 distance)>`.

### Decisive source
```rust
// toy_vector_sparse_ivf.rs:1505-1515 + :1565-1574 — score truth comes from the TABLE:
let result = return_if_io!(main.seek(SeekKey::TableRowId(rowid), SeekOp::GE { eq_only: true }));
if !matches!(result, SeekResult::Found) {
    return Err(LimboError::Corrupt(
        "vector_sparse_ivf corrupted: unable to find rowid in main table".to_string(),
    ));
}
// ... re-read column at configuration.columns[0].pos_in_table, validate Float32Sparse:
let distance = operations::jaccard::vector_distance_jaccard(&data, &arg)?;
dists.insert((FloatOrd(distance), *rowid));
if dists.len() > *limit as usize {
    let _ = dists.pop_last();
}
```

**Flow:** posting run ends ⇒ `current.sort_unstable()` (:1383/:1438) → EvaluateSeek pops one rowid, seeks the MAIN table (missing rowid ⇒ Corrupt — index references must resolve) → EvaluateRead re-reads the live column value and computes the EXACT weighted Jaccard (`1 − min_sum/max_sum`, merge-walk of sorted component lists; **max_sum==0 ⇒ NaN**, jaccard.rs :121-124) → insert into `distances`, evict worst with `pop_last()` once over limit. When all components drain, Seek builds `search_result` from the ordered set in ONE step and returns `Done(!empty)` (:1249-1250); `query_rowid` peeks front (InternalError if drained early), `query_next` pops.
**Invariant:** `FloatOrd` wraps `f64::total_cmp` (:148-151) giving a TOTAL order so `(distance, rowid)` pairs are safely BTreeSet-orderable despite NaN/±0.0. Because scoring happens during query_start, the returned bool already reflects post-MVCC visibility and the K best rows — `results_materialized: true` is earned by this buffering, which is also why all statement hooks here are no-ops.
**Probe:** executed at HEAD: `test_vector_sparse_ivf_insert_query` asserts per-row `query_rowid`/`query_column` sequences and that `query_next` flips false exactly when exhausted (tests/integration/index_method/mod.rs:226-239). Anchors verified byte-exact: `total_cmp` :150, `pop_last` :1573, Corrupt-on-missing-rowid :1510-1514.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "vector_distance_jaccard FloatOrd search_result", limit: 10 });
```
resolves `FloatOrd.cmp` :149-151, `EvaluateRead` :1526-1586, jaccard dispatcher `core/vector/mod.rs:152-165`, sparse kernel `jaccard.rs:91-125`.

## Verdict
Adopt "index nominates, table decides" — rescoring from authoritative storage makes the index free to be lossy. Adopt total_cmp-wrapped ordering for any float-keyed ordered set. Adapt eviction (pop_last vs heap) to K's size. Omit eager NaN handling: turso lets NaN propagate as a never-inserted oddity rather than special-casing it. Coverage: no_recorded_issue on both cited paths.
