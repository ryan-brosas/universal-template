<!-- capsule-v2 -->
# BuildRecordWhereClause — spec→visitor→where with empty-where null

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a record spec become a `WHERE` expression, and how is the empty-where case signalled to callers?

## Record where clause builder
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/buildRecordWhereClause.ts` (whole file, 19-39).
**Signature:** `buildRecordWhereClause(spec, options?): Result<Expression<SqlBool> | null, DomainError>`.
**Data Shape:** wraps `TableRecordConditionWhereVisitor`; returns `null` when the visitor's `where()` yields the empty-where validation error.

### Decisive source
```ts
const visitor = new TableRecordConditionWhereVisitor(options);
const acceptResult = spec.accept(visitor);
if (acceptResult.isErr()) return err(acceptResult.error);
const whereResult = visitor.where();
if (whereResult.isErr()) {
  if (whereResult.error.code === 'validation.invalid' &&
      whereResult.error.message === EMPTY_WHERE_ERROR) return ok(null); // empty → null
  return err(whereResult.error);
}
return ok(whereResult.value as unknown as Expression<SqlBool>);
```

**Flow:** construct visitor (with table/host aliases) → `spec.accept(visitor)` (accumates conditions) → `visitor.where()` → map the empty-where error to `null` so callers skip the WHERE; any other error propagates.

**Invariant:** The empty-where sentinel is a specific validation error (`code=validation.invalid`, `message='Empty where condition'`) that is deliberately converted to `null` rather than a failure; all other errors propagate as DomainErrors.

**Probe:** exercised by `record/repository/PostgresTableRecordQueryRepository.pglite.spec.ts` and the condition-where spec (specs with no conditions compile to a null where).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildRecordWhereClause EMPTY_WHERE_ERROR visitor.where", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the accept→where funnel and the empty-where→null conversion. Adapt the visitor options (aliases). Omit nothing portable. Probes pinned to the real specs.
