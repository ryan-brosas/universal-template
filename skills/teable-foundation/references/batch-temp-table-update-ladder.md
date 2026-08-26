<!-- capsule-v2 -->
# Temp-table batch UPDATE with typed error translation — how do you bulk-update heterogeneous rows under a unique-constraint failure without losing the offending field?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the exact choreography of `batchUpdateDB`, and why must temp table + update + drop share ONE transaction?

## batchUpdateDB
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/batch.service.ts:batchUpdateDB` (:303–423).
**Signature:** `batchUpdateDB(dbTableName, idFieldName, schemas: {schemaType, dbFieldName}[], data: {id, values}[], routingTableId?)`.
**Data Shape:** `data` rows carry per-record value dicts; `schemas` declares each updated column's driver-agnostic type (`dbType2knexFormat`).

### Decisive source
```ts
const createTempTableSql = createTempTableSchema
  .toQuery()
  .replace('create table', 'create temporary table');
...
await this.databaseRouter.dataPrismaTransactionForTable(resolvedRoutingTableId, async (tx) => {
  // temp table should in one transaction
  await tx.$executeRawUnsafe(createTempTableSql);
  await tx.$executeRawUnsafe(insertTempTableSql);
  await handleDBValidationErrors({
    fn: async () => { await tx.$executeRawUnsafe(updateRecordSql); },
    handleUniqueError: async () => { /* re-query field meta → localized duplicate error naming field ids */ },
    handleNotNullError: async () => { /* same ladder for NOT NULL */ },
  });
  await tx.$executeRawUnsafe(dropTempTableSql);
});
```

**Flow:** Create per-call temp table (10-char nanoid suffix) typed from `schemas` → dbProvider emits INSERT-into-temp + UPDATE…FROM(temp) SQL → run all four statements inside ONE routed transaction so PG drops the temp table on commit/rollback even after failures → constraint violations are translated by RE-QUERYING metadata to name the exact fields in user-facing errors. Callers (`executeUpdateRecordsInner` :424–475) pre-filter computed/link fields, convert cell→db values, and bump `__version` client-side; `executeUpdateRecords` (:285–302) groups opsData by identical field-set key so each SQL shape is uniform.
**Invariant:** Temp-table lifetime == transaction lifetime; splitting them leaks session tables on error paths. Error translation must happen INSIDE `handleDBValidationErrors` while the tx can still roll back cleanly — converting after the throw outside loses which field violated.
**Probe:** `grep -cF 'create temporary table' apps/nestjs-backend/src/features/calculation/batch.service.ts` → 2; `grep -cF 'handleUniqueError' <same>` → 1; `grep -cF '__version: version + 1' <same>` → present in executeUpdateRecordsInner.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "batchUpdateDB temporary table executeUpdateRecordsSqlList", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt temp-table JOIN-update as the portable bulk-mutation primitive with strict tx-scoped lifecycle and metadata-driven constraint translation; adapt to your SQL emitter; omit teable's routing fallback (`findFirstOrThrow` when no routingTableId) if single-db.
