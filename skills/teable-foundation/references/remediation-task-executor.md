<!-- capsule-v2 -->
# Remediation-task executor — how does teable route a queued index/search remediation task to the right runner and keep it from ever touching a real user object?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** A generic `table_query_remediation_task` row can mean a manual investigation, a schema-change search rebuild, a search-vector rebuild, or a plain btree/gin index create. How does the executor dispatch each and guard the DDL?

## Kind-dispatch executor with managed-name + large-rewrite guards
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/executor.ts` — `PostgresTableQueryRemediationExecutor.execute` (43–134), `.executeSearchVectorSchemaMaintenance` (136–154), `.findTableMeta` (156–164), `splitPhysicalName` (173–182), `buildIndexFieldSql` (184–200), `buildIndexName` (202–205), `isSchemaMaintenancePayload` (167–171).
**Signature:** `execute(ctx, {task, allowManualIndexExecution}): Promise<Result<unknown, DomainError>>`.
**Data Shape:** task snapshot = `{kind, tableId, baseId, payload, status, attempts, maxAttempts}`; payload for index tasks = `{fieldDbName?, fieldId?, fields[{fieldId?, fieldDbName?, direction?}], indexKind:'btree'|'gin_trgm'}`; schema-maintenance payload carries `{trigger:'schema_change', reason}`.

### Decisive source
```ts
const manualSearchVectorTaskKinds = { create_search_access_path: true, rebuild_search_access_path: true,
                                      create_search_vector: true, rebuild_search_vector: true };
// dispatch order:
if (task.kind === 'manual_investigation') return ok({ skipped: true, reason: 'manual investigation task' });
if ((kind==='rebuild_search_access_path'||kind==='rebuild_search_vector') && isSchemaMaintenancePayload(payload))
  return this.executeSearchVectorSchemaMaintenance(ctx, task);   // → reconciler.maintainAfterSchemaChange
if (!input.allowManualIndexExecution) return ok({ skipped: true, reason: 'manual index execution disabled' });
if (manualSearchVectorTaskKinds[task.kind]) { /* new PostgresTableSearchVectorExecutor(...).execute(...) */ }
// plain index task:
if (fields.length === 0 || !payload.indexKind) return err(validation 'table_query_ops.invalid_index_task_payload');
const indexName = buildIndexName(tableId, fields.map(f=>f.fieldDbName??'').join('_'), payload.indexKind); // tqops_<tableId>_<field>_<kind> ≤60
await sql.raw(`CREATE INDEX CONCURRENTLY IF NOT EXISTS ${quote(indexName)} ON ${tableSql} USING ${using} (${fieldSql})`).execute(dataDb);
```

**Flow:** `manual_investigation` short-circuits to a skipped result → schema-maintenance payloads route to the reconciler (which re-analyzes and rebuilds the search vector with `allowLargeTableRewrite:false`) → if `allowManualIndexExecution` is false, skip → search-vector kinds delegate to `PostgresTableSearchVectorExecutor` → otherwise validate the payload (fields + indexKind required) → resolve the physical table from `table_meta` (`base_id` + `db_table_name`, splitting `schema.table`) → build the `tqops_`-prefixed index name → `CREATE EXTENSION IF NOT EXISTS pg_trgm` for gin_trgm → `CREATE INDEX CONCURRENTLY IF NOT EXISTS`.
**Invariant:** every search-vector DDL path is re-guarded by `assertManagedSearchVectorNames` inside the executor; plain index tasks get a `tqops_`-prefixed, length-capped name and are created `CONCURRENTLY IF NOT EXISTS`; a missing/invalid payload is a validation error, never a silent no-op; manual index execution is an explicit opt-in flag.
**Probe:** `executor.spec.ts:21` `describe('PostgresTableQueryRemediationExecutor')` — `:26` 'routes manual search-vector rebuilds to the search-vector executor'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableQueryRemediationExecutor executeSearchVectorSchemaMaintenance buildIndexName", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the kind-dispatch ladder with explicit manual-execution gating and managed-name prefixing; adapt the index-name prefix and length caps to host; omit teable's search-vector schema-maintenance branch if the host has no managed search vector. Coverage caveat: `executor.ts` is parse_partial at :1–206 (the WHOLE file is flagged), so the graph may miss constructs inside it — the source above was read directly and is authoritative.
