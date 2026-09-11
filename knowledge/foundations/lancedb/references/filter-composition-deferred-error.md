<!-- capsule-v2 -->
# Filter composition with deferred error — what happens when a builder receives multiple or mixed-representation filters?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** When `.only_if()` / `.only_if_expr()` is called repeatedly, how are filters combined and where do combination failures surface?

## AND-composition + deferred failure
**Path/Symbol:** `rust/lancedb/src/query.rs:and_filters` (792–812), `QueryRequest::add_filter` (915–929), `QueryRequest::check_filter` (934–941); consumed at `rust/lancedb/src/table/query.rs:create_plan` (line 140).
**Signature:** `fn and_filters(existing: QueryFilter, new: QueryFilter) -> Result<QueryFilter>`; `pub(crate) fn add_filter(&mut self, new: QueryFilter)`; `pub(crate) fn check_filter(&self) -> Result<()>`.
**Data Shape:** `QueryFilter` is a 3-variant enum: `Sql(String)`, `Substrait(Arc<[u8]>)`, `Datafusion(Expr)`. Combination failures are stored in `QueryRequest.filter_error: Option<String>` (private), surfaced only at plan time.

### Decisive source
```rust
(QueryFilter::Sql(lhs), QueryFilter::Sql(rhs)) => Ok(QueryFilter::Sql(format!("({lhs}) AND ({rhs})"))),
(QueryFilter::Datafusion(lhs), QueryFilter::Datafusion(rhs)) => Ok(QueryFilter::Datafusion(lhs.and(rhs))),
(QueryFilter::Sql(lhs), QueryFilter::Datafusion(rhs)) => {
    let rhs = crate::expr::expr_to_sql_string(&rhs)?;
    Ok(QueryFilter::Sql(format!("({lhs}) AND ({rhs})")))
}
_ => Err(Error::InvalidInput { message: "cannot combine a Substrait filter with another filter".to_string() }),
```
```rust
Err(err) => {
    // The filters were consumed while attempting to combine
    // them; the recorded error is surfaced by `check_filter`
    // before the query executes.
    self.filter_error = Some(err.to_string());
    return;
}
```

**Flow:** Builder methods return `Self` (not `Result`), so a failed combination cannot fail the builder call — `add_filter` records the error string and DROPS both filters (they were consumed by value), leaving `filter = None` with `filter_error = Some(...)`. Every backend's `create_plan` must call `check_filter()` FIRST, converting the stored string back into an InvalidInput error before any scan runs.
**Invariant:** A SINGLE filter is left byte-identical — no parens added (upstream test pins `"id > 0"` unchanged). Mixed SQL+expression lowers the expression to SQL text; Substrait never combines (hard error at add time → deferred). A porter who replaces the earlier filter instead of AND-ing silently narrows results; a porter who panics in the builder breaks the fluent API; a porter who forgets `check_filter` turns a user mistake into a silent unfiltered scan.
**Probe:** `cargo test -p lancedb --lib query::tests::test_repeated_only_if_combines_with_and` (pins parenthesized SQL composition, expression .and() composition, mixed lowering, and successful execution of the combined filter).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "and_filters add_filter check_filter QueryFilter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way composition matrix and the record-now/fail-at-plan pattern (it is what lets the builder stay chainable); adapt the expression→SQL lowering to whatever expression system the host uses; omit Substrait support if the host has no substrait representation. Direct-test coverage present (dedicated upstream test).
