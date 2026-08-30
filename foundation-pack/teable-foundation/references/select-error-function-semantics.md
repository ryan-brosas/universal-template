<!-- capsule-v2 -->
# select-error-function-semantics — What SQL implements ERROR()/IS_ERROR() in the SELECT compiler, and why does it differ from generated columns?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How can a SELECT-side formula deliberately raise while its generated-column twin must not?

## error() = zero-row advisory-unlock trick; isError() = constant FALSE — mutable SQL allowed on read paths
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/select-query/postgres/select-query.postgres.ts:error`/`isError` (:1706-1717); xor multi-param parity arm (:1698-1704).
**Signature:** `error(_message: string): string`; `isError(_value: string): string`.
**Data Shape:** error emits `(SELECT pg_catalog.pg_advisory_unlock_all() WHERE FALSE)` — a subquery that is valid immutable-looking syntax but executes row-by-row semantics; generated columns cannot contain subqueries at all.

### Decisive source
```ts
error(_message: string): string {
  // In SELECT context, we can use functions that raise errors
  return `(SELECT pg_catalog.pg_advisory_unlock_all() WHERE FALSE)`;
}

isError(_value: string): string {
  // Check if value would cause an error - simplified implementation
  return `FALSE`;
}
```

**Flow:** formula containing ERROR(...) compiled for a live query → the WHERE-FALSE projection evaluates per candidate row and aborts the statement when reached (with a confusing-but-real error), while ISERROR(x) short-circuits to false so guarded formulas never trip.
**Invariant:** the class doc draws the line ("Unlike generated columns, these CAN use mutable functions and have different optimization strategies") — porting this emitter into a STORED column definition fails DDL (subqueries banned). IS_ERROR's constant-false means teable never actually evaluates error-ness; it relies on typed-null degradation elsewhere.
**Probe:** static byte-exact: `grep -n 'pg_advisory_unlock_all' select-query.postgres.ts` → :1712; contrast probe `grep -c 'pg_advisory_unlock_all' generated-column-query.postgres.ts` → 0.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"isError error","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the read-path-only escape hatch and document why. Adapt message plumbing (teable discards it). Omit nothing.
