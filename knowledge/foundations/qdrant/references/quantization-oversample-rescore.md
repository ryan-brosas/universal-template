<!-- capsule-v2 -->
# Quantization oversample + rescore — how does a quantized segment return exact-quality top-k?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** How are `oversampling` and `rescore` applied around a quantized HNSW search, and what are the defaults?

## Oversampled top, optional exact rescore
**Path/Symbol:** `lib/segment/src/index/vector_index_search_common.rs`: `is_quantized_search` (:15-25), `get_oversampled_top` (:27-45), `postprocess_search_result` (:48-91); default values in `lib/segment/src/types.rs` (`default_quantization_oversampling_value` :615).
**Signature:** `fn get_oversampled_top<Q: QuantizedVectorsRead>(quantized_storage: Option<&Q>, params: Option<&SearchParams>, top: usize) -> usize`; `postprocess_search_result(..., top, hw) -> OperationResult<Vec<ScoredPointOffset>>`.
**Data Shape:** `SearchParams.quantization: Option<QuantizationSearchParams{ignore, rescore, oversampling}>`; oversampling is `Option<f64>`; output of search truncated to user `top`.

### Decisive source
```rust
pub fn get_oversampled_top(...) -> usize {
    let quantization_enabled = is_quantized_search(quantized_storage, params);
    let oversampling_value = params.and_then(|p| p.quantization)
        .map(|q| q.oversampling).unwrap_or(default_quantization_oversampling_value());
    match oversampling_value {
        Some(oversampling) if quantization_enabled && oversampling > 1.0 =>
            (oversampling * top as f64) as usize,
        _ => top,
    }
}
// postprocess:
let rescore = quantization_enabled && params.and_then(|p| p.quantization)
    .and_then(|q| q.rescore).unwrap_or(default_rescoring);
if rescore {
    let mut scorer = FilteredScorer::new(vector.to_owned(), vector_storage,
        None::<&Q>, /* no filter context */ None, point_deleted, hardware_counter)?;
    search_result = scorer.score_points(&mut search_result.iter().map(|x| x.idx).collect_vec(), 0).collect();
    search_result.sort_unstable();
    search_result.reverse();
}
search_result.truncate(top);
```

**Flow:** decide quantized mode (`Some(storage) && !ignore && !exact`) → widen candidate pool to ceil(oversampling×top) BEFORE search (regular path searches `oversampled_top` candidates; graph-with-vectors uses `max(ef, oversampled_top)` as ef) → after search, optionally re-score surviving ids with FULL vectors (quantized storage explicitly passed as `None::<&Q>`), sort descending → truncate to `top`.
**Invariant:** (1) oversampling multiplies the *candidate* count, never ef alone — both paths consume it differently but neither leaves it unused when quantization is on; (2) rescore drops any filter context — candidates were already filter-checked during traversal, rescoring must not re-filter or sparse filters with deferred points could shrink the result below top; (3) truncation happens exactly once, at postprocess; (4) `exact=true` bypasses everything (is_quantized_search false → plain top, no rescore).

**Probe:** `grep -c default_quantization_oversampling_value lib/segment/src/index/vector_index_search_common.rs lib/segment/src/types.rs | awk -F: '{s+=$NF} END{print s}'` → prints `4` (2 import/use in search_common + serde default attr :592 + definition :615 in types.rs; multi-file grep counts LINES, sum them). Direct tests: `lib/segment/tests/integration/hnsw_quantized_search_test.rs::check_oversampling` (:271-328); strict-mode validation `tests/openapi/test_strictmode.py::test_strict_mode_search_max_oversampling_validation` (:495).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "get_oversampled_top postprocess_search_result rescore score_points truncate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt candidate-widening then single-truncate pipeline and the no-refilter-rescore rule. Adapt defaults (`DEFAULT_QUANTIZATION_OVERSAMPLING`, ignore flag) to host config. Omit turbo/async quantization variants.
