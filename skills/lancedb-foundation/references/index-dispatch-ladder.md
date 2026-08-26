<!-- capsule-v2 -->
# Index type dispatch ladder — how does Index::Auto and each builder map to Lance params, and which defaults surprise?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** Given an `Index` variant and a field, what exact Lance parameters are derived, and what does Auto choose?

## make_index_params + get_index_type_for_field
**Path/Symbol:** `rust/lancedb/src/table/create_index.rs:make_index_params` (181–388), `get_index_type_for_field` (391–416), helpers `build_ivf_params` (68–84), `get_num_sub_vectors` (87–102), `resolve_index_field` (153–178).
**Signature:** `pub(super) async fn make_index_params(&self, field: &Field, index_opts: Index) -> Result<Box<dyn lance::index::IndexParams>>`.
**Data Shape:** 12 variants: Auto, BTree, Bitmap, LabelList, Fm, FTS, IvfFlat, IvfSq, IvfPq, IvfRq, IvfHnsw{Pq,Sq,Flat}. Output: `(column, Box<dyn IndexParams>, IndexType)`.

### Decisive source
```rust
Index::Auto => {
    if supported_vector_data_type(field.data_type()) {
        // Use IvfPq as the default for auto vector indices
        let dim = Self::get_vector_dimension(field)?;
        let ivf_params = lance_index::vector::ivf::IvfBuildParams::default();
        let num_sub_vectors = Self::get_num_sub_vectors(None, dim, None);
        let pq_params = lance_index::vector::pq::PQBuildParams::new(num_sub_vectors as usize, 8);
        let lance_idx_params = VectorIndexParams::with_ivf_pq_params(MetricType::L2, ivf_params, pq_params);
// ...
let num_sub_vectors = Self::get_num_sub_vectors(index.num_sub_vectors, dim, index.num_bits);
if num_bits.is_some_and(|num_bits| num_bits == 4) && !suggested.is_multiple_of(2) {
    // num_sub_vectors must be even when 4 bits are used
    suggested + 1
} else { suggested }
```

**Flow:** (1) single-column only — multi-column composite indexes error up front; (2) column resolved CASE-INSENSITIVELY through nested field paths (`resolve_case_insensitive`) and re-canonicalized; (3) Auto ⇒ IvfPq(L2, default IVF, 8-bit PQ) for vector-typed fields else BTree for scalar-typed; (4) every explicit variant validates the field dtype via the `supported_*_data_type` predicate family BEFORE building params (Bitmap additionally refuses whole-document JSON fields with guidance to use a JSON-path scalar or FTS); (5) IVF partitioning accepts EITHER `num_partitions` OR `target_partition_size` (None,None → Lance default); (6) PQ sub-vectors: user value wins, else suggested from dim, bumped to EVEN when 4-bit codes are used.
**Invariant:** The dtype validation happens at PARAM-BUILD time in this SDK layer, not deep in Lance — a porter who skips it defers errors to mid-build. Auto's IvfPq-with-L2 choice is load-bearing for recall expectations; distance-type mismatch between query and index silently invalidates results (documented on `VectorQueryRequest.distance_type`). HNSW variants always pass `HnswBuildParams::default().num_edges(m).ef_construction(..)` — m/ef_construction only, other knobs stay defaults.
**Probe:** `cargo test -p lancedb --lib table::create_index::tests::test_create_index` (pins Auto→IvfPq, L2 distance, single segment, stats surface; sibling test `test_ivf_pq_uses_default_partition_size_for_num_partitions` pins partition derivation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "make_index_params IvfPqIndexBuilder get_num_sub_vectors", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the variant→params ladder incl. Auto defaults and the 4-bit even-sub-vector bump; adapt supported-dtype predicates to host schema types; omit remote/job-wait plumbing (`execute_async` waiters) unless porting job semantics too. Direct-test coverage present (multiple in-module integration tests).
