<!-- capsule-v2 -->
# top_k = limit + offset pre-offsetting — why does the scanner receive a k larger than the requested limit?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** When a vector search has both limit and offset, how is pagination correctness achieved before the scanner's limit stage?

## create_plan nearest call
**Path/Symbol:** `rust/lancedb/src/table/query.rs:create_plan` (231–238), contrasted with LSM arm guard at `rust/lancedb/src/table/query/lsm.rs` (701).
**Signature:** within `pub async fn create_plan(table: &NativeTable, query: &AnyQuery, options: ...)`: `let top_k = query.base.limit.unwrap_or(DEFAULT_TOP_K) + query.base.offset.unwrap_or(0); scanner.nearest(&column, query_vector, top_k)?;`.
**Data Shape:** DEFAULT_TOP_K=10 (`rust/lancedb/src/query.rs:36`). limit: Option<usize>, offset: Option<usize> from the shared QueryRequest.

### Decisive source
```rust
let top_k = query.base.limit.unwrap_or(DEFAULT_TOP_K) + query.base.offset.unwrap_or(0);
if is_binary {
    let query_vector = arrow::compute::cast(&query_vector, &DataType::UInt8)?;
    scanner.nearest(&column, query_vector, top_k)?;
} else {
    scanner.nearest(&column, query_vector.as_ref(), top_k)?;
}
```

**Flow:** ANN searches return the k nearest candidates; requesting only `limit` then applying offset later would skip real results. So the KNN arm fetches `limit+offset` candidates and lets `scanner.limit(limit, offset)` trim the head afterwards — pagination equals a slice of the unpaginated result (upstream pagination tests assert slice-equality for page sizes 3 and 10 across scan/FTS/vector queries). Binary vectors get an extra cast of the QUERY VECTOR to UInt8 before nearest.
**Invariant:** top_k must be computed BEFORE scanner.limit is set, and offset participates in candidate count but not in returned rows. The LSM vector arm instead clamps `k = max(limit,1)` (offset applied by paging) — do not copy one arm's formula into the other.
**Probe:** `cargo test -p lancedb --lib query::tests::test_pagination_with_vector_query` (asserts paginated pages equal full-result slices).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "top_k nearest scanner.limit offset pagination", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt candidate-count pre-offsetting for any ANN+pagination combination; adapt constant names; omit binary-cast branch if the host lacks uint8 vectors. Direct-test coverage present (dedicated pagination test suite).
