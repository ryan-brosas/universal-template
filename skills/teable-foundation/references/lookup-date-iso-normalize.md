<!-- capsule-v2 -->
# lookup-date-iso-normalize — Why do multi-value lookups over datetime targets re-format elements to ISO UTC strings?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What transformation is applied to date-like targets inside json_agg and why only there?

## to_char AT TIME ZONE 'UTC' into a fixed ISO-8601 pattern, wrapped back as jsonb — multi-value only
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:visitLookupField` (:470-483).
**Signature:** guard: `driver === Pg && field.isMultipleCellValue && isDateLikeField(targetLookupField) && targetLookupField.dbFieldType === DbFieldType.DateTime`.
**Data Shape:** output element becomes `to_jsonb('<YYYY-MM-DD"T"HH24:MI:SS.MS"Z">')` string; single-value lookups untouched.

### Decisive source
```ts
// For Postgres multi-value lookups targeting datetime-like fields, normalize the
// element expression to an ISO8601 UTC string so downstream JSON comparisons using
// lexicographical ranges (jsonpath @ >= "..." && @ <= "...") behave correctly.
// Do NOT alter single-value lookups to preserve native type comparisons in filters.
const isoUtcExpr = `to_char(${expression} AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')`;
expression = `to_jsonb(${isoUtcExpr})`;
```

**Flow:** detect date-like target under a MULTI-value lookup → convert timestamptz to UTC then to the fixed-width ISO string → re-wrap as jsonb so json_agg still emits valid JSON. Downstream conditional filters compare lexicographically.
**Invariant:** the comment draws the boundary explicitly: normalizing single-value lookups would BREAK native type comparisons (timestamptz >= timestamptz) in filters; lexicographic correctness only matters inside JSON arrays where every element must share one comparable shape. A porter who "unifies" both paths breaks single-value date filters.
**Probe:** static byte-exact: `grep -n "AT TIME ZONE 'UTC', 'YYYY-MM-DD" field-cte-visitor.ts` → :480.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"isoUtcExpr","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the dual-path rule (normalize arrays, never scalars). Adapt pattern/timezone constants. Omit nothing else.
