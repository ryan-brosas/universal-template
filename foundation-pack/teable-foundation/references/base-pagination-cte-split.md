<!-- capsule-v2 -->
# base-pagination-cte-split — How does the v1 record query builder paginate without computing CTEs for rows outside the page?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Where do limit/offset apply so link/lookup CTE work is bounded to the requested page?

## Split pagination over a BASE CTE
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:applyBasePaginationIfNeeded` (:424-531) + `resolveBaseLimit` (:546-559).
**Signature:** `private applyBasePaginationIfNeeded(qb, table, state, alias, params: {limit?, offset?, filter?, sort?, currentUserId?, defaultOrderField?, hasSearch?, restrictRecordIds?, paginationMode?: 'split'|'full'}): void`.
**Data Shape:** mutates the shared `qb`: wraps the original source as `BASE_<alias>` CTE and re-froms the builder from it; records the name in state (`state.setBaseCteName`). Default mode `'split'`.

### Decisive source
```ts
const safeOffset = offset && offset > 0 ? offset : 0;
const baseLimit = paginationMode === 'full' ? limit : this.resolveBaseLimit(limit, offset);
...
if (applyPagination && baseLimit) {
  baseBuilder.limit(baseLimit);
  if (paginationMode === 'full' && safeOffset > 0) {
    baseBuilder.offset(safeOffset);
  }
}
...
const baseCteName = `BASE_${alias}`;
qb.with(baseCteName, baseBuilder);
qb.from({ [alias]: baseCteName });
state.setBaseCteName(baseCteName);
state.setMainTableSource(baseCteName);
```

**Flow:** resolve base limit → skip entirely when no limit/offset AND no restrictRecordIds → collect required field ids (filter+sort+defaultOrder) → if any required field is computed (lookup/rollup/conditional-rollup/formula) DISABLE pagination (fall back to full scan; see computed-pagination-fallback) → build BASE subquery selecting `alias.*` with filter/sort/default-order/limit (+offset only in 'full') + optional `WHERE __id IN (restrictRecordIds)` → register CTE and repoint main source.
**Invariant:** In `'split'` mode the BASE CTE holds `(offset+limit)` rows and the OUTER query applies offset later — CTE rows beyond the page are still materialized but never past `offset+limit`. `resolveBaseLimit` returns `undefined` for negative/-1 limits (meaning unbounded), so pagination silently disables rather than emitting LIMIT -1.
**Probe:** `grep -n 'safeOffset + limit' apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts` → exactly :554 inside `resolveBaseLimit`; `grep -c "paginationMode === 'full'"` on same file → 2.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"applyBasePaginationIfNeeded","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the split-BASE-CTE pagination shape whenever downstream CTEs join off the paged relation. Adapt the `BASE_` prefix and `-1 means unlimited` convention to host conventions. Omit teable's `hasSearch` interplay (search path forces full scan by its own gate).
