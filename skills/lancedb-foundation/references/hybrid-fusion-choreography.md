<!-- capsule-v2 -->
# Hybrid fusion choreography — in what order do rank, normalize, and rerank run, and what must both arms share?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** When `nearest_to` and `full_text_search` are set on one query, how is the single fused result produced, and what ordering would a porter get wrong?

## Execute_hybrid pipeline
**Path/Symbol:** `rust/lancedb/src/query.rs:VectorQuery::execute_hybrid` (1372–1444).
**Signature:** `async fn execute_hybrid(&self, options: QueryExecutionOptions) -> Result<SendableRecordBatchStream>`.
**Data Shape:** Inputs: self.request (VectorQueryRequest whose `base.full_text_search` is Some and `query_vector` non-empty). Intermediate: two independent RecordBatch streams collected fully into memory. Output: ONE RecordBatch (single_batch_stream re-slices to max_batch_length) containing `_relevance_score`.

### Decisive source
```rust
let mut fts_query = Query::new(self.parent.clone());
fts_query.request = self.request.base.clone();
fts_query = fts_query.with_row_id();

let mut vector_query = self.clone().with_row_id();
vector_query.request.base.full_text_search = None;
let (fts_results, vec_results) = try_join!( ... )?;
// ...
if matches!(self.request.base.norm, Some(NormalizeMethod::Rank)) {
    vec_results = hybrid::rank(vec_results, DIST_COL, None)?;
    fts_results = hybrid::rank(fts_results, SCORE_COL, None)?;
}
vec_results = hybrid::normalize_scores(vec_results, DIST_COL, None)?;
fts_results = hybrid::normalize_scores(fts_results, SCORE_COL, None)?;
let reranker = self.request.base.reranker.clone()
    .unwrap_or(Arc::new(RRFReranker::default()));
let mut results = reranker.rerank_hybrid(&fts_query.query.query(), vec_results, fts_results).await?;
check_reranker_result(&results)?;
let limit = self.request.base.limit.unwrap_or(DEFAULT_TOP_K);
if results.num_rows() > limit { results = results.slice(0, limit); }
if !self.request.base.with_row_id { results = results.drop_column(ROW_ID)?; }
```

**Flow:** (1) Clone the request into TWO queries — FTS-only and vector-only — and force `with_row_id()` on BOTH (row id is the join key for fusion); (2) strip `full_text_search` from the vector arm so it does not recurse into hybrid; (3) run both arms concurrently via `try_join`, collecting under `without_output_batch_length_limit()` (max_batch_length=0 so intermediate batches are unbounded); (4) `concat_batches` each side into one batch using `hybrid::query_schemas` (handles empty sides by renaming DIST_COL↔SCORE_COL, see hybrid-score-normalization capsule); (5) if `norm == Rank`, replace scores with competition ranks FIRST; (6) min-max normalize both columns (distance NOT inverted here); (7) rerank with the user reranker or default `RRFReranker{k:60}` — note the argument order `(query, vector_results, fts_results)`; (8) enforce `_relevance_score` exists; (9) slice to limit; (10) drop `_rowid` unless explicitly requested.
**Invariant:** Row-id forcing happens BEFORE execution — a porter who joins on row position instead of `_rowid` mis-fuses whenever the two arms return different row sets. Distance is normalized as-is (largest distance → 1.0); inverting is the reranker's job, not the pipeline's.
**Probe:** `cargo test -p lancedb --lib query::tests::test_hybrid_search` (pins cross-arm membership: "cat" arrives via vector arm, "b" via FTS arm; also covers zero-FTS-match case).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "VectorQuery execute_hybrid hybrid fusion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the forced-row-id dual-arm join, the rank→normalize→rerank ordering, and the default-to-RRF fallback; adapt the concurrency shape (try_join) to host async runtime; omit the remote/server variant of hybrid dispatch. Coverage caveat: pinned by upstream tests `test_hybrid_search`, `test_hybrid_query_execute_with_options_respects_max_batch_length`, `test_hybrid_search_empty_table`.
