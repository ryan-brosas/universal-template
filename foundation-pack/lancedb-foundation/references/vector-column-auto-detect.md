<!-- capsule-v2 -->
# Vector column auto-detection — how is "the" vector column chosen when none is named, and why does dimension matter?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** What resolution rule finds the vector column for an unnamed `.nearest_to()` / index build, and which errors fire?

## default_vector_column
**Path/Symbol:** `rust/lancedb/src/utils/mod.rs:default_vector_column` (151–175) + recursive `collect_vector_columns` (177–205).
**Signature:** `pub(crate) fn default_vector_column(schema: &Schema, dim: Option<i32>) -> Result<String>`.
**Data Shape:** Walks top-level fields AND struct children carrying a path stack; a candidate is any field whose `infer_vector_dim(data_type)` succeeds AND whose dim matches when supplied; returns canonical dotted field path.

### Decisive source
```rust
if candidates.is_empty() {
    Err(Error::InvalidInput {
        message: format!("No vector column found to match with the query vector dimension: {}",
                         dim.unwrap_or_default()) })
} else if candidates.len() != 1 {
    Err(Error::Schema {
        message: format!("More than one vector columns found, please specify which column
                          to create index or query: {:?}", candidates) })
} else { Ok(candidates[0].clone()) }
```

**Flow:** Called from `Query::nearest_to` fallback paths in `create_plan` (both plain and multi-vector arms) and the LSM vector arm, ALWAYS with `Some(query_vector.len())` as dim — so dimension filtering is effectively mandatory at query time; index creation calls it without dim. Struct children recurse with accumulated paths so nested vectors resolve as dotted paths.
**Invariant:** Ambiguity is an ERROR, never silent first-match — a two-vector-column table forces explicit `.column(...)`. The error message distinguishes "none matched YOUR DIMENSION" from "several exist" because the common failure mode is a dim mismatch, not absence.
**Probe:** `cargo test -p lancedb --lib query_base_methods_on_vector_query` (pins the dim-mismatch error text "No vector column found to match with the query vector dimension: 3").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "default_vector_column collect_vector_columns infer_vector_dim", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt unique-candidate-or-error resolution with dim filtering; adapt infer_vector_dim to host vector-type predicates; omit struct-path recursion if the host flattens schemas. Direct-test coverage present (error-text assertion in upstream test).
