<!-- capsule-v2 -->
# Hostile-numeric coercion ladder — how do text-typed multi-value cells still SUM?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How are numeric aggregates computed when the underlying jsonb elements are TEXT (lookup over singleLineText, mixed link values)?

## toNumericSafe strip→NULLIF→cast
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/aggregation-query/postgres/multiple-value/multiple-value-aggregation.adapter.ts:toNumericSafe` (:4–8); used by `max`/`min`/`sum`/`average` (:19–53).
**Signature:** `toNumericSafe(columnExpression: string): string`.
**Data Shape:** Input jsonb-array element text; output `double precision` or NULL.

### Decisive source
```ts
private toNumericSafe(columnExpression: string): string {
  const textExpr = `(${columnExpression})::text`;
  const sanitized = `REGEXP_REPLACE(${textExpr}, '[^0-9.+-]', '', 'g')`;
  return `NULLIF(${sanitized}, '')::double precision`;
}
```

**Flow:** Element → force `::text` (jsonb scalars may arrive quoted) → REGEXP_REPLACE deletes every character outside `[0-9.+-]` ("$1,234 USD" → "1234") → empty result becomes NULL (not zero) → cast to double precision. SUM/AVG/MIN/MAX then ignore NULLs per SQL semantics.
**Invariant:** Strip-before-cast is what makes aggregates never ERROR on hostile cell text — a bare `::double precision` on "abc" throws and kills the whole statistics endpoint. The NULLIF-empty rung is load-bearing: after stripping, "" would fail the cast, so it must become NULL first. Contrast with the v2 rollup coercion capsule (`lookup-rollup-json-aggregation`) which validates-and-coerces instead of stripping — v1 aggregation deliberately trades precision for never-failing. Porters who reorder NULLIF after the cast reintroduce the crash.
**Probe:** `grep -cF 'NULLIF' apps/nestjs-backend/src/db-provider/aggregation-query/postgres/multiple-value/multiple-value-aggregation.adapter.ts` → 1; `grep -cF "REGEXP_REPLACE" apps/nestjs-backend/src/db-provider/aggregation-query/postgres/multiple-value/multiple-value-aggregation.adapter.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "toNumericSafe REGEXP_REPLACE NULLIF double precision", limit: 10 });
```

## Verdict
Adopt strip→NULLIF→cast for user-controlled text feeding numeric SQL aggregates; adapt the kept-character class to your locale needs; omit if your column typing is already numeric.
