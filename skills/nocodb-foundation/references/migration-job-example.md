<!-- capsule-v2 -->
# Migration-job worked example — how does a concrete versioned migration (nc_job_008) implement the runner contract: batched table rename with per-dialect SQL and collision-avoiding suffixes?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does an individual migration service implement the versioned-runner `job()` contract, and what per-dialect + collision invariants does a data migration maintain?

## batched meta-table scan + dialect-aware rename + collision-avoiding suffix
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_008_recover_disconnected_table_name.ts:RecoverDisconnectedTableNames` (whole, 232L); runner contract `init-migration-jobs.ts` (see migration-jobs capsule).
**Signature:** `async job(): Promise<boolean>` — returns true only when the migration fully completed (advances the versioned runner's `version`).
**Data Shape:** `renameTableSql` per dialect (mysql/mariadb `RENAME TABLE ?? TO ??`; pg/sqlite `ALTER TABLE ?? RENAME TO ??`); `PARALLEL_LIMIT = +process.env.NC_ORDER_MIGRATION_PARALLEL_LIMIT || 10`; `processingModels` list guards re-processing; `SimpleLRUCache(1000)` caches `Source` lookups.

### Decisive source
```ts
// pg binds '?' placeholders positionally; a table name containing '?' would break knex raw
const replaceQuestionMarkWithPlaceholderPg = (tableName) =>
  tableName.split('?').reduce((tn, token, i) => { if (i > 0) token = '$' + i + token; tn += token; return tn; }, '');
// collision-avoiding rename: if target exists, append _1, _2, ...
while (await checkIfTableNameExists(baseModel, replacingTableName, dbDriver)) {
  replacingTableName = `${initialTableName}_${counter}`; counter++;
}
await dbDriver.raw(renameTableSql[source.type], [tableName, replacingTableName]);
await ncMeta.metaUpdate(workspaceId, baseId, MetaTable.MODELS, { table_name: replacingTableName }, model.id);
```
```ts
// job() loop: repeatedly select the next batch of affected models, process each, until none remain
while (true) {
  const modelsToProcess = await this.getModelsToBeProcessedQueryBuilder(ncMeta)
    .select([...]).whereNotIn(`${MetaTable.MODELS}.id`, this.processingModels.map(m => m.fk_model_id))
    .orderBy('id', 'asc').limit(PARALLEL_LIMIT * 2);
  if (!modelsToProcess?.length) break;
  for (const model of modelsToProcess) { this.processingModels.push({fk_model_id: model.id, processing: true});
    try { await this.processModel(model, ncMeta); } catch (ex) { this.log('Error', ex.message); } }
  await new Promise(r => setTimeout(r, 1000));   // yield between batches
}
return true;
```

**Flow:** the query builder selects models whose `table_name` contains `?` or `$` (disconnected names) from meta sources (`is_meta` or `is_local`). The job loops in batches of `PARALLEL_LIMIT*2`, marking each id in `processingModels` (so a crash-and-restart doesn't reprocess mid-batch), renaming the physical table via the dialect-specific SQL, then updating the meta `table_name` to match. A collision (target name already exists) appends `_1`, `_2`, … until free. On pg, `?` in a table name is rewritten to `$N` placeholders before the raw query, and the replacement name strips `$N`/`?` to `_`. Per-model errors are logged and swallowed (the loop continues); the job returns `false` only on an outer failure.

**Invariant:** the physical table rename and the meta `table_name` update must BOTH happen — a rename without the meta update leaves the model pointing at a missing table. Dialect matters: `RENAME TABLE` (mysql) vs `ALTER TABLE RENAME TO` (pg/sqlite) and the `?`→`$N` placeholder rewrite are pg-specific. The `processingModels` guard prevents re-processing a model already in flight across the batched loop. Returning `true` only on full completion is what lets the versioned runner advance (a partial/crashed run returns falsy and retries next time).

**Probe:** no unit test upstream. Source-grounded probe: `nc_job_008...ts:13-19` (renameTableSql dialect table) vs `:107-136` (batched loop + processingModels) and `:198-225` (collision suffix + rename + metaUpdate).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "RecoverDisconnectedTableNames renameTableSql processingModels getModelsToBeProcessedQueryBuilder", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the batched meta-scan loop with an in-flight guard, dialect-aware rename SQL, collision-avoiding suffixes, and physical+meta write cohesion; adapt the query predicate, batch size, and dialect map to host. Omit the specific disconnected-table-name predicate unless porting that migration. Coverage caveat: no in-repo tests; source-grounded.
