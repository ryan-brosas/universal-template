<!-- capsule-v2 -->
# Multi-vector union plan — what output schema do N query vectors produce, and how is List-typed input different?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** When `add_query_vector` is called multiple times, how does one plan become N plans, and when do they concatenate instead?

## create_multi_vector_plan + multivector fork
**Path/Symbol:** `rust/lancedb/src/table/query.rs:create_multi_vector_plan` (334–381) and the multivector fork inside `create_plan` (170–217).
**Signature:** `pub(crate) fn create_multi_vector_plan(plans: Vec<Arc<dyn ExecutionPlan>>) -> Result<Arc<dyn ExecutionPlan>>`.
**Data Shape:** Output batch gains a leading `query_index: Int32` column (0-based index of the contributing query vector); total rows ≈ Σ per-vector limits; row order NOT guaranteed.

### Decisive source
```rust
if let DataType::List(_) = vector_field.data_type() {
    // Multivector handling: concatenate into FixedSizeList<FixedSizeList<_>>
    ... fsl_builder.finish() ...            // ONE plan, concatenated query vector
} else {
    // Multiple query vectors: create a plan for each and union them
    let plans = try_join_all(plan_futures).await?;
    return create_multi_vector_plan(plans);
}
```
```rust
let projected_plans = plans.into_iter().enumerate().map(|(plan_i, plan)| {
    let query_index_expr = Arc::new(Literal::new(ScalarValue::Int32(Some(plan_i as i32))));
    let mut projections = vec![(query_index_expr, "query_index".to_string())];
    projections.extend_from_slice(&project_all_columns);
    ProjectionExec::try_new(projections, plan).unwrap()
});
let unioned = UnionExec::try_new(projected_plans)?;
RepartitionExec::try_new(unioned, Partitioning::RoundRobinBatch(1))
```

**Flow:** If the TARGET COLUMN is `List<T>` (multivector/MuVec column): all query vectors are packed into a FixedSizeList<FixedSizeList<f32>> and a SINGLE search runs (colbert-style). Otherwise EACH vector becomes its own cloned request planned recursively and joined concurrently; each sub-plan gets a literal `query_index` projection prepended; UnionExec concatenates; RoundRobinBatch(1) repartition collapses to one output partition.
**Invariant:** `query_index` is prepended FIRST so column order stays stable across sub-plans; empty plan list is an InvalidInput error (never an empty union). A porter who forgets the repartition-to-one produces interleaved partitions breaking downstream collect-and-slice logic.
**Probe:** `cargo test -p lancedb --lib query::tests::test_multiple_query_vectors` (pins UnionExec presence, exactly one result per query vector, and query_index containing both 0 and 1 unordered).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "create_multi_vector_plan query_index UnionExec add_query_vector", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-vector-plan + tagged-union shape and the List-column concat exception; adapt DataFusion exec nodes to host plan primitives; omit namespace pushdown interplay. Direct-test coverage present (test_multiple_query_vectors).
