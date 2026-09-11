<!-- capsule-v2 -->
# Row-limit write plugin — how is a table row ceiling enforced for every record-creating write path without a DB trigger?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does the plugin pipeline host a count-check that resolves its limit per-space and guards twice (before and inside persistence)?

## Policy-resolved limit + prepare/guard/beforePersist double-check
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresTableRowLimitPlugin.ts` whole (185L): `ITableRowLimitPolicy` (:8-12), `StaticTableRowLimitPolicy` (:14-20), `SpaceCreditTableRowLimitPolicy` (:22-51: table_meta→base→space join reading `space.credit`, fallback on NULL), `PostgresTableRowLimitPlugin` (:58-179), create-count switch (`getCreateCount` :162-178: createOne/submit/duplicate=1; duplicateStream/createMany/createStream/importAppend=payload.recordCount; paste=payload.createRecordCount).
**Signature:** `supports(op) = recordWriteOperationMayCreateRecords(op)`; error code `validation.limit.rows_per_table_max`.
**Data Shape:** prepared state `{dbTableName, maxRowCount}` or undefined (non-creating ops short-circuit at prepare).

### Decisive source
```ts
const db = resolvePostgresDbOrTx(this.db, context.executionContext, 'data');   // count in DATA plane
const countResult = await sql<{count:string}>`
  select count(*) as count from ${sql.table(preparedState.dbTableName)}`.execute(db);
const rowCount = Number(countResult.rows[0]?.count ?? 0);      // PG returns bigint as STRING
if (rowCount + recordCount > preparedState.maxRowCount)
  return err(domainError.validation({ code: 'validation.limit.rows_per_table_max',
    details: { max, maxRowCount, rowCount, recordCount } }));
```

**Flow:** plugin runner phases → supports gates to creating ops only → prepare resolves dbTableName + policy limit ONCE → guard re-checks before mutation and beforePersist again inside the persistence frame → both run the same COUNT(*) + projected-sum check.
**Invariant:** The check counts EXISTING rows plus incoming count against the limit — under concurrency two simultaneous imports can each pass then overshoot (accepted race; the ceiling is quota-grade, not transactional). Count runs on the resolved data-plane tx so it sees uncommitted sibling writes of the same operation. The credit policy degrades silently to the fallback when the legacy column is absent — never errors.
**Probe:** `PostgresTableRowLimitPlugin.spec.ts:86/:102/:124/:137/:149` — five direct specs incl. credit-fallback twins.
**Coverage caveat:** none — behavior matrix fully tested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableRowLimitPlugin SpaceCreditTableRowLimitPolicy getCreateCount", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt policy-object limits + phase-double-check + string-bigint handling; adapt the credit join to your billing model; document the concurrency overshoot as accepted semantics, don't "fix" it with locks.
