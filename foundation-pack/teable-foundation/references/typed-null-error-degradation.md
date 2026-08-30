<!-- capsule-v2 -->
# typed-null-error-degradation — What SQL does a broken field (deleted target, errored formula) emit in SELECT lists?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do lookups, links, rollups, and formulas degrade when their dependency graph is broken?

## dialect.typedNullFor(dbFieldType) — never a bare NULL, never a throw
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/providers/pg-record-query-dialect.ts:typedNullFor` (:390-413); call sites `field-select-visitor.ts` (:226-228 buildTypedNull + lookup :253-262/:320-327, link :455-462, rollup :489-495/:502-508) and `field-cte-visitor.ts:buildPhysicalFieldExpression` (:843-849).
**Signature:** `typedNullFor(dbFieldType: DbFieldType): string`.
**Data Shape:** Json→`NULL::jsonb`, Integer→`NULL::integer`, Real→`NULL::double precision`, DateTime→`NULL::timestamptz`, Boolean→`NULL::boolean`, Blob→`NULL::bytea`, Text/default→`NULL::text`.

### Decisive source
```ts
// field-cte-visitor — even PHYSICAL reads of an errored field become typed nulls:
private buildPhysicalFieldExpression(field: FieldCore, alias: string): string {
  if (field.hasError) {
    return this.dialect.typedNullFor(field.dbFieldType);
  }
  return `"${alias}"."${field.dbFieldName}"`;
}
```

**Flow:** visitor meets `field.hasError` (or missing lookupOptions / missing CTE / non-link lookupOptions on a rollup) → emits the dialect-typed NULL → registers it in the selection map so downstream filter/sort still resolve the id → query succeeds with NULL cells.
**Invariant:** bare `NULL` would force Postgres to infer unknown type and break `UPDATE … FROM (SELECT …)` assignments into typed physical columns; typing the null keeps every consumer's cast valid. Degradation is per-field: one broken lookup must not fail the whole record list.
**Probe:** upstream direct spec pins sibling typed-null behavior via `pg-record-query-dialect.spec.ts`; static byte-exact: `grep -n "'NULL::text'" providers/pg-record-query-dialect.ts` → :406; `grep -n 'typedNullFor' field-select-visitor.ts | head -3`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"typedNullFor","limit":3,"detail":"ids"}'
```

## Verdict
Adopt typed-null degradation for every computed-field failure mode. Adapt type map. Omit nothing.
