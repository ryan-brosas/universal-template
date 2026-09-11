<!-- capsule-v2 -->
# Null-Aware Keyset Cursor Algebra — why do strict operator twins (`eqStrict`/`isStrictly`) exist and how does the cursor condition use them?

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `twenty-crm`. **Question:** How does cursor (keyset) pagination build its continuation predicate so it never skips or duplicates rows around the SQL NULL block, given that ordinary filters widen empty values into NULL?

## Single-home null-aware keyset condition builder
**Path/Symbol:** `packages/twenty-server/src/engine/api/utils/build-cursor-keyset-condition.utils.ts` : `buildCursorKeysetCondition` (lines 25–69); leaf wrapper `build-cursor-leaf-where-condition.utils.ts` (lines 9–46); scan-order resolution `get-effective-scan-order.utils.ts`.
**Signature:** `buildCursorKeysetCondition({ cursorValue, orderByDirection, isForwardPagination, isEqualityCondition, canFieldHoldNullValue, buildLeafCondition, buildNullCheckCondition? }): Record<string, unknown> | null` (overloads: equality variant always returns a condition; range variant may return `null`).
**Data Shape:** returns GraphQL-filter-shaped objects (`{ gt: v }`, `{ isStrictly: 'NULL' }`, `{ or: [...] }`) that RE-ENTER the normal filter compiler via `buildCursorLeafWhereCondition`'s path fold (`leaf.path.reduceRight((nested, key) => ({ [key]: nested }), leafFilter)`).

### Decisive source
```ts
// The strict operators compare exactly: the empty-value widening of 'is'
// and 'eq' does not mirror the SQL scan order the cursor continues
buildNullCheckCondition = (isNull) =>
  buildLeafCondition({ isStrictly: isNull ? 'NULL' : 'NOT_NULL' }),

if (isEqualityCondition) {
  return cursorValue === null
    ? buildNullCheckCondition(true)
    : buildLeafCondition({ eqStrict: cursorValue });
}

const { isAscending, areNullsScannedLast } = getEffectiveScanOrder(
  orderByDirection, isForwardPagination,
);

if (cursorValue === null) {
  // Inside the leading NULL block only the tie-breaking keys can advance the
  // scan; inside the trailing one nothing sorts after on this key at all
  return areNullsScannedLast ? null : buildNullCheckCondition(false);
}

const mainCondition = buildLeafCondition({
  [isAscending ? 'gt' : 'lt']: cursorValue,
});

if (areNullsScannedLast && canFieldHoldNullValue) {
  return { or: [mainCondition, buildNullCheckCondition(true)] };
}
return mainCondition;
```
And in compute-where-condition-parts.ts:
```ts
// Exact variants used by keyset pagination conditions: cursor continuation
// must mirror the SQL scan order, where only actual SQL NULLs sort into the
// NULL block, so the empty-value widening of 'is' and 'eq' would skip or
// duplicate rows around the block boundaries
case 'isStrictly': ...
case 'eqStrict':   ...
```

**Flow:** for each ORDER BY key rung: equality rung → `eqStrict` value or strict IS NULL; range rung → direction-mapped `gt/lt`; if nulls sort LAST and the field can hold NULL → OR with strict `IS NULL` branch; if the cursor itself sits in the trailing NULL block → return `null` and let the caller drop this key's or-branch entirely (tie-breakers advance). Rungs combine left-to-right as `[or(...), and(eqStrict-rung0, or-rung1), ...]`.
**Invariant:** the continuation predicate must be the exact mirror of the effective SQL scan order — widening operators are forbidden here because they would pull stored-empty rows across NULL-block boundaries (skip/duplicate). Returning `null` (not an empty condition) is the honest signal that no row sorts strictly after the cursor on this key.
**Probe:** `engine/api/utils/__tests__/compute-cursor-arg-filter.utils.spec.ts:266–274` pins `{ or: [{ name: { gt: 'John' } }, { name: { isStrictly: 'NULL' } }] }, { and: [{ name: { eqStrict: 'John' } }, ...] }` including composite `fullName.firstName` shapes (278–355); integration behavior pinned by `test/integration/graphql/suites/cursor-pagination-order-by.integration-spec.ts` (`paginateForward` 54–96, `paginateBackwardFrom` 98–132). RUNNER BLOCKED: jest not executable in this checkout; assertions verified by direct read.

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "twenty-crm", query: "buildCursorKeysetCondition null aware keyset pagination strict cursor scan order", limit: 6, fields: ["signature"] });
// → buildCursorKeysetCondition 31-69 (rank 1); getEffectiveScanOrder 15-29;
//   integration suites cursor-pagination-order-by.integration-spec.paginateForward/paginateBackwardFrom
```

## Verdict
Adopt the algebra wholesale: strict-twin operators for cursor predicates, or-with-NULL-block when nulls scan last, null-return when the cursor is in the trailing block, filter-shaped output re-entering the normal compiler. Adapt `getEffectiveScanOrder` to your ASC/DESC + NULLS FIRST/LAST grammar. Omit the overridable `buildNullCheckCondition` unless you have relation keys whose NULL block is better matched through another column.
