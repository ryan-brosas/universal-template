<!-- capsule-v2 -->
# Generated audit-column stripping — why must INSERT values drop legacy GENERATED ALWAYS columns?

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do writes survive tables whose audit columns are still physically `GENERATED ALWAYS` while field metadata says they are writable?

## Physical-generation triage
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordRepository.ts:stripPhysicallyGeneratedColumnsFromInsertValues` (:1263–1270, :1614–1621), `syncAutoNumberSequence` (:812–830), `analyzeSeededTable` (:845–851); builder side `record/query-builder/insert/RecordInsertBuilder.ts:isPersistedAsGeneratedColumn` gates (:252–288).
**Signature:** `stripPhysicallyGeneratedColumnsFromInsertValues(db, tableName, candidateColumnNames: string[], valuesRows: Array<Record<string, unknown>>): Promise<void>`; called AFTER values are assembled, immediately before the INSERT loop.
**Data Shape:** candidates come from `collectUserAuditFieldColumnNames(table)` (CreatedBy/LastModifiedBy field columns); the DB introspection asks which of those are actually generated.

### Decisive source
```ts
// Legacy CreatedBy/LastModifiedBy columns may still be GENERATED ALWAYS even when
// field meta says otherwise — strip them so PostgreSQL accepts the INSERT (T6146).
await stripPhysicallyGeneratedColumnsFromInsertValues(
  db, tableName, collectUserAuditFieldColumnNames(table), [valuesWithViewOrder]
);
```
Builder mirror — skip writing the column entirely and remember it as a snapshot slot:
```ts
if (isCreatedBy || isLastModifiedBy) {
  const persistedAsGenerated = yield* isPersistedAsGeneratedColumn(field);
  if (persistedAsGenerated) { continue; }        // PostgreSQL rejects explicit values
  userFieldColumns.push({ dbFieldName, systemColumn }); // snapshot filled from context
}
```

**Flow:** metadata says writable → builder prepares a JSON user snapshot (`{id,title,email,avatarUrl}` built ONCE from the execution context, `buildUserFieldJsonValue`) → the strip pass re-checks physical reality and deletes offending keys from every row → INSERT succeeds either way. The same gate decides whether `__auto_number` restores need `setval()` resync afterwards.
**Invariant:** trust the DB over field metadata for what may be written; the snapshot JSON is derived from `__created_by`/`__last_modified_by` system columns at read time, so dropping the explicit value never loses data. Never emit an explicit value for a GENERATED ALWAYS column.
**Probe:** `record/repository/PostgresTableRecordRepository.insert.pglite.spec.ts` ('returns stored insert snapshots from mutation capture'; 'splits wide insertMany batches…' pins the surrounding pipeline).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "stripPhysicallyGeneratedColumnsFromInsertValues GENERATED ALWAYS audit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the "introspect-before-write" strip pass and the context-built snapshot pattern (kills per-row user subqueries in batch inserts). Adapt the column-name collection to your audit schema. Omit teable's T6146 migration history.
