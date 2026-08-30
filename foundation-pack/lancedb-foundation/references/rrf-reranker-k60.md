<!-- capsule-v2 -->
# RRF reranker k=60 — what exact score does each row get and which side wins on duplicates?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** How does the default Reciprocal Rank Fusion combine vector and FTS rankings, including duplicate row ids?

## RRF scoring + merge
**Path/Symbol:** `rust/lancedb/src/rerankers/rrf.rs:RRFReranker::rerank_hybrid` (47–149); trait default merge in `rust/lancedb/src/rerankers.rs:Reranker::merge_results` (67–96).
**Signature:** `async fn rerank_hybrid(&self, _query: &str, vector_results: RecordBatch, fts_results: RecordBatch) -> Result<RecordBatch>`; `fn merge_results(&self, vector_results: RecordBatch, fts_results: RecordBatch) -> Result<RecordBatch>`.
**Data Shape:** Both inputs must carry a UInt64 `_rowid` column (loud InvalidInput listing found columns otherwise). Accumulator `BTreeMap<u64, f32>` keyed by row id. Output: merged batch + appended `_relevance_score` Float32 non-null, sorted descending by it.

### Decisive source
```rust
let mut update_score_map = |(i, result_id)| {
    let score = 1.0 / (i as f32 + self.k);
    rrf_score_map.entry(result_id).and_modify(|e| *e += score).or_insert(score);
};
vector_ids.values().iter().enumerate().for_each(&mut update_score_map);
fts_ids.values().iter().enumerate().for_each(&mut update_score_map);
// merge_results (trait default):
let combined = concat_batches(&fts_results.schema(), [vector_results, fts_results].iter())?;
row_ids.values().iter().for_each(|id| {
    mask.append_value(unique_ids.insert(id));
});
```

**Flow:** (1) For EACH input list independently, walk rows in list order; row at 0-based position `i` contributes `1/(i+k)` (k defaults to 60; `RRFReranker::new(k)` overrides) to that row id's accumulator; (2) `merge_results` concatenates `[vector_results, fts_results]` — VECTOR SIDE FIRST — and keeps the first occurrence of each row id (BTreeSet-insert mask), so duplicate rows retain their vector-arm column values; (3) look up every surviving row id in the accumulator (`.unwrap()` — valid because every merged row came from one of the two lists); (4) sort_to_indices descending + `take` reorder all columns; (5) append `_relevance_score`.
**Invariant:** Position weights start at `1/(0+k)` for rank 0 (the upstream test with k=1 documents `foo = 1/1` for the top hit) — a porter who uses 1-based ranks shifts every score. Scores are summed ACROSS lists only; within a list order is positional. Concat order makes the vector arm authoritative for duplicated rows' payload columns.
**Probe:** `cargo test -p lancedb --lib rerankers::rrf::test::test_rrf_reranker` (pins exact scores bar=1.5, foo=1.0, bean=0.75, dog=0.533…, baz=0.333 and final order `[bar, foo, bean, dog, baz]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "RRFReranker rerank_hybrid reciprocal rank fusion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 0-based `1/(i+k)` formula, BTreeMap accumulation, and first-occurrence-wins dedup; adapt the Arrow take/sort mechanics to host columnar library; omit the Python/Node reranker variants (different language SDKs, same formula). Direct-test coverage present (unit test with hand-computed expected scores).
