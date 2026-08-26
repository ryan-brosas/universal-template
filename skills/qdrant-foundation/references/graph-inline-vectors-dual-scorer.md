<!-- capsule-v2 -->
# Graph-with-inline-vectors dual scorer — how do quantized link vectors and full base vectors cooperate in one HNSW search?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `ext-qdrant`. **Question:** When the graph stores vectors inline, which vector scores traversal and which scores the final result, and when is this path refused?

## Two scorers, one traversal
**Path/Symbol:** `lib/segment/src/index/hnsw_index/hnsw/read_view/search.rs`: `search_with_vectors` closure (:88-135) vs `regular_search` (:137-170); dispatch (:172-178).
**Signature:** `graph.search_with_vectors(top, max(ef, oversampled_top), &link_scorer_filtered, &link_scorer_filtered_bytes, base_scorer_bytes, custom_entry_points, &is_stopped)`.
**Data Shape:** link scorer = `FilteredScorer::new(query, vector_storage, Some(quantized_vectors), filter_context, deleted_points, hw)`; base scorer = plain `vector_storage.build_raw_scorer(...)`; both expose `scorer_bytes()` fast paths; output bypasses `postprocess_search_result`.

### Decisive source
```rust
// Quantized vectors are "link vectors"
let Some(quantized_vectors) = self.quantized_vectors else { return Ok(None); };
let link_scorer_filtered = FilteredScorer::new(vector.to_owned(), self.vector_storage,
    Some(quantized_vectors), /* filter_context */ ..., deleted_points, ...)?;
let Some(link_scorer_filtered_bytes) = link_scorer_filtered.scorer_bytes() else { return Ok(None); };
// Full vectors are "base vectors"
let base_scorer = self.vector_storage.build_raw_scorer(vector.to_owned(), ...)?;
let Some(base_scorer_bytes) = base_scorer.scorer_bytes() else { return Ok(None); };
Ok(Some(self.graph.search_with_vectors(top, std::cmp::max(ef, oversampled_top),
    &link_scorer_filtered, &link_scorer_filtered_bytes, base_scorer_bytes,
    custom_entry_points, &vector_query_context.is_stopped())?))
// dispatch:
if let Some(search_result) = search_with_vectors()? { Ok(search_result) } else { regular_search() }
```
Gate conditions (all must hold, else fall through to `regular_search`):
```rust
match algorithm { SearchAlgorithm::Hnsw => (), SearchAlgorithm::Acorn => return Ok(None), }
if !self.graph.has_inline_vectors() || !is_quantized_search(self.quantized_vectors, params) {
    return Ok(None);
}
```

**Flow:** refuse if ACORN was selected (not implemented for graphs-with-vectors), no inline vectors, quantization disabled/ignored/exact requested, or either scorer lacks a bytes fast path → otherwise traverse with quantized link vectors + filter context, then re-score the final candidates with FULL base vectors inside the graph search itself — note this path returns directly and does NOT run `postprocess_search_result`, because rescoring already happened.
**Invariant:** (1) link scoring may be lossy (quantized) but final top must be scored on full vectors; (2) the four refusal conditions are independent — a porter collapsing them into one check changes semantics (e.g. exact=true must silently take the regular path); (3) ef for this path is `max(ef, oversampled_top)` while regular search passes `oversampled_top` as top with plain `ef`; (4) filter context is built identically in both paths (`payload_index.filter_context(f, &hw_counter)`).

**Probe:** `grep -c "search_with_vectors\|has_inline_vectors" lib/segment/src/index/hnsw_index/hnsw/read_view/search.rs` → prints `4`. Coverage caveat: pinned indirectly by hnsw integration suites; no test names this closure.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-qdrant", query: "has_inline_vectors scorer_bytes search_with_vectors link base", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-scorer split (lossy links, exact finals) and the explicit refusal ladder. Adapt scorer construction to host storage traits; the bytes-fast-path optionality can map to SIMD dispatch. Omit mmap-residency plumbing of inline storage (`StorageGraphLinksVectors::try_new` silent-failure-on-build noted separately).
