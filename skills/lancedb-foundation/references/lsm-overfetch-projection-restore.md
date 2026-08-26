<!-- capsule-v2 -->
# LSM over-fetch factor 2.0 + projection restore — why does the LSM arm fetch double, and where do leaked PK columns go?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** What keeps LSM result pages filled despite cross-generation dedup, and how is the user's projection restored after internal PK appends?

## Over-fetch + restore_projection
**Path/Symbol:** `rust/lancedb/src/table/query/lsm.rs:LSM_OVERFETCH_FACTOR` (47–51), `fts_plan`/`vector_plan` `.with_overfetch_factor(LSM_OVERFETCH_FACTOR)` (468, 703), `restore_projection` (607–636).
**Signature:** `const LSM_OVERFETCH_FACTOR: f64 = 2.0;` applied via `LsmScanner::with_overfetch_factor`; `fn restore_projection(plan: Arc<dyn ExecutionPlan>, query: &VectorQueryRequest, pk_columns: &[String]) -> Result<Arc<dyn ExecutionPlan>>`.

### Decisive source
```rust
/// Over-fetch factor for the LSM vector/FTS arms. With the default of `1.0` a
/// source blocked by cross-generation PK dedup fetches exactly `k` and can return
/// fewer than `k` live rows; upserts routinely create such blocked candidates, so
/// widen the per-source fetch to keep result pages filled.
const LSM_OVERFETCH_FACTOR: f64 = 2.0;
```
```rust
// Keep a column unless it is a pk column the user did not select (this preserves
// user columns and score columns like `_distance`, dropping only leaked pk).
let keep: Vec<_> = schema.fields().iter().enumerate()
    .filter(|(_, f)| selected.iter().any(|c| c == f.name())
                                || !pk_columns.iter().any(|pk| pk == f.name()))
    ...
if keep.len() == schema.fields().len() { return Ok(plan); }   // no-op fast path
Ok(Arc::new(ProjectionExec::try_new(keep, plan)?))
```

**Flow:** Vector and FTS arms wrap the scanner with over-fetch 2.0 so that candidates blocked by newer same-PK rows in another generation don't shrink the returned page below `limit` (plain scans rely on limit/offset paging instead). After planning, `restore_projection` drops primary-key columns Lance appended internally for dedup unless the user's explicit `Select::Columns` named them; `Select::All` legitimately includes PK and is untouched; score columns (`_distance`) survive because they're not PK.
**Invariant:** Without the 2× fetch, an upsert-heavy table returns SHORT pages (fewer than limit) even though matching rows exist — a porter who treats over-fetch as a tuning nicety ships a pagination-visible bug. The restore filter is keep-if-selected OR not-a-pk — never drop user columns, never add a projection when nothing changes.
**Probe:** `grep -n 'LSM_OVERFETCH_FACTOR' rust/lancedb/src/table/query/lsm.rs` (constant wired into both arms); behavior pinned by LSM integration tests upstream; `restore_projection` logic mirrors `resolve_single_index_dedupes_segments` module tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "with_overfetch_factor restore_projection ProjectionExec pk columns", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt result-page-fill over-fetch on any dedup-before-limit path and the leak-only-pk projection restore; adapt the constant to host page-fill telemetry; omit plain-scan over-fetch (paging handles it there). Coverage caveat: factor value justified by in-source rationale comment; no standalone unit test isolates the 2.0.
