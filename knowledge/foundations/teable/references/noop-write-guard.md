<!-- capsule-v2 -->
# No-op write guard — why must an UPDATE that changes nothing still count as applied, and how does the WHERE clause enforce it in SQL?

**Source:** teable AGPL `develop@06a4461e`. **Question:** How does teable prevent a same-value update from bumping versions/undo rows, and what does the repository return when zero rows matched?

## IS DISTINCT FROM per-column OR + matched-zero ⇒ mutationApplied:false
**Path/Symbol:** `PostgresTableRecordRepository.ts` — module-level `buildDistinctUserFieldWhere(table, setClauses)` (:119–150); consumption in `updateOne` (:2156–2173: `if (changedFieldColumns.length > 0 && !updatedRow) { abort(); return ok({ mutationApplied: false }); }`); bulk variant :2358–2361. Tests: `PostgresTableRecordRepository.updateMany.pglite.spec.ts` 'does not update selector-matched rows when requested values are unchanged' (:506), 'does not update explicit stream rows when requested values are unchanged' (:568).
**Signature:** `(table, setClauses) => Result<Expression<SqlBool> | undefined, DomainError>`.

### Decisive source
```ts
for (const field of table.getFields()) {
  if (isTrackedLastModifiedField(field)) continue;          // skip __last_modified_time/by
  const dbFieldNameValue = yield* dbFieldName.value();
  if (SYSTEM_UPDATE_COLUMNS.has(dbFieldNameValue) ||
      !Object.prototype.hasOwnProperty.call(setClauses, dbFieldNameValue)) continue;
  conditions.push(sql`${sql.ref(dbFieldNameValue)} IS DISTINCT FROM ${setClauses[dbFieldNameValue]}`);
}
return ok(conditions.length ? sql`(${sql.join(conditions, sql` OR `)})` : undefined);
// updateOne:
let updateQuery = db.updateTable(tableName).set(setClauses).where('__id', '=', recordIdStr);
if (distinctUserFieldWhere) updateQuery = updateQuery.where(distinctUserFieldWhere);
```

**Flow:** build one extra predicate per SET column — `col IS DISTINCT FROM newvalue` — OR-ed together, skipping system/audit columns → AND it into the UPDATE's WHERE → if RETURNING yields no row while changed-field columns were requested, treat as "no mutation happened": abort the snapshot session cleanly and return `{ mutationApplied: false }`, NOT an error.
**Invariant:** THREE facts a porter gets wrong: (1) plain `col <> value` drops NULL rows (NULL <> x is NULL ⇒ filtered out), so a no-op update on a NULL-valued cell would still fire; `IS DISTINCT FROM` is the only NULL-safe inequality — this guard is what keeps unchanged writes from manufacturing version bumps and undo-log rows (tests :506/:568 pin row counts). (2) "No-op" is detected via EMPTY RETURNING, which requires the changed-field RETURNING columns to be requested at all — the `changedFieldColumns.length === 0` path cannot distinguish no-match from no-op. (3) lastModifiedTime/By fields are excluded from the predicate because their own values change every write; they must never gate it.
**Probe:** updateMany.pglite.spec.ts :506/:568 pin that unchanged-value writes leave rows untouched.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildDistinctUserFieldWhere IS DISTINCT FROM mutationApplied", limit: 5 });
```
## Verdict
Adopt verbatim: NULL-safe no-op guards (`IS DISTINCT FROM` OR-ladder) belong in the WHERE of any optimistic-versioned record store, with an explicit mutationApplied:false result path instead of an error.
