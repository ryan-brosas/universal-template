<!-- capsule-v2 -->
# conditional-rollup-ordering-functions — Which rollup functions honor sort+limit inside a conditional rollup, and how is the ordered slice aggregated?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do array_join/concatenate/array_unique/array_compact consume an ORDER BY + LIMIT slice of foreign rows?

## rollupFunctionSupportsOrdering gate → orderByRaw on the source subquery → LIMIT only when ordering
**Path/Symbol:** gate `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:rollupFunctionSupportsOrdering` (:998-1008); application :1416-1436 (orderBy) / :1438-1441 (limit) in `generateConditionalRollupFieldCteForScope`; dialect STRING_AGG arms (`pg-record-query-dialect.ts:543-589`).
**Signature:** `private rollupFunctionSupportsOrdering(expression: string): boolean` over parsed fn name; sort via options.sort `{fieldId, order}`; limit via `normalizeConditionalLimit(limit)`.
**Data Shape:** ordering fns aggregate the formatted display expression for link/formula/conditional targets (useFormattedForArrayFunctions), others aggregate raw.

### Decisive source
```ts
if (supportsOrdering && sort?.fieldId) {
  const sortField = foreignTable.getField(sort.fieldId);
  if (sortField) {
    ensureLinkDependencies(sortField);
    let sortExpression = this.resolveConditionalComputedTargetExpression(sortField, ...);
    ...alias rewrite...
    orderByClause = `${sortExpression} ${sort.order === SortFunc.Desc ? 'DESC' : 'ASC'}`;
  }
}
...
if (supportsOrdering && orderByClause) aggregateSourceQuery.orderByRaw(orderByClause);
if (supportsOrdering) aggregateSourceQuery.limit(resolvedLimit);
```

**Flow:** parse rollup expression name → ordering-capable? → resolve sort field (generating ITS dependencies too) → order source subquery → apply normalized limit ONLY on ordering path (non-ordering fns must see all rows) → aggregate via STRING_AGG(... ORDER BY ...) / jsonb_agg ORDER BY arms.
**Invariant:** limit without ordering would truncate nondeterministically, so the two are bound: `canUseEqualityPlan` additionally requires NO sort/limit — ordering functions always take the correlated fallback plan, never the counts-join plan. Unknown rollup names throw.
**Probe:** static byte-exact: `grep -n 'supportsOrdering && orderByClause' field-cte-visitor.ts` → :1424/:1550 region; upstream spec pins STRING_AGG ordering shape indirectly through dialect spec.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"rollupFunctionSupportsOrdering","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the capability gate + ordered-slice aggregation. Adapt fn registry. Omit nothing.
