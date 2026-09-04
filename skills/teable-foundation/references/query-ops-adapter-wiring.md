<!-- capsule-v2 -->
# Query-ops adapter wiring — how does teable register the whole query-ops Postgres adapter into its DI container and resolve the dual-DB split?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** The adapter wires ~10 readers/executors into the container, distinguishes meta vs data DB, and shares one reconciler under two tokens. What's the registration shape and the dual-DB fallback?

## registerV2TableOpsPostgresAdapter wiring
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/register.ts` — `registerV2TableOpsPostgresAdapter` (56–166), `RegisterV2TableOpsPostgresAdapterOptions` (42–50); `tokens.ts` — `v2TableOpsPostgresTokens` (1–5); `helpers.ts` — `getTablePhysicalName` (10–21), `quoteIdentifier` (23), `makePhysicalTableSql` (25–26), `toInfrastructureError` (4–8).
**Signature:** `registerV2TableOpsPostgresAdapter(container, rawOptions?): Promise<DependencyContainer>`.
**Data Shape:** options = `{metaDb?, dataDb?, ensureSchema?, lifecycle?}`; tokens = `{config, metaDb, dataDb}` Symbols.

### Decisive source
```ts
const metaDb = rawOptions.metaDb ?? (container.isRegistered(v2MetaDbTokens.db) ? container.resolve(v2MetaDbTokens.db) : undefined);
if (!metaDb) throw new Error('Missing table ops metaDb');
const dataDb = rawOptions.dataDb ?? (container.isRegistered(v2DataDbTokens.db) ? container.resolve(v2DataDbTokens.db) : (metaDb as unknown as ...)); // dataDb FALLS BACK to metaDb
if (rawOptions.ensureSchema) await ensureTableQueryOpsSchema(opsMetaDb);
container.registerInstance(v2TableOpsPostgresTokens.config, parsed.data);
// one reconciler instance under TWO tokens (searchVectorReconciler AND searchAccessPathReconciler):
const searchVectorReconciler = new PostgresTableSearchVectorReconciler(unknownMetaDb, unknownDataDb);
container.registerInstance(v2TableOpsTokens.searchVectorReconciler, searchVectorReconciler);
container.registerInstance(v2TableOpsTokens.searchAccessPathReconciler, searchVectorReconciler);
// executor depends on the core table repository + the reconciler:
new PostgresTableQueryRemediationExecutor(unknownMetaDb, unknownDataDb, container.resolve<ITableRepository>(v2CoreTokens.tableRepository), searchVectorReconciler)
```

**Flow:** parse/validate options via zod → resolve metaDb from options or the container's `v2MetaDbTokens.db` (required) → resolve dataDb from options, the container's `v2DataDbTokens.db`, or fall back to metaDb (single-DB mode) → optionally `ensureSchema` → register config/metaDb/dataDb instances → register the observation repo under both sink and reader tokens → register physical-stats reader, index inspector, plan validator, recommendation/task/lease repos → construct ONE reconciler and register it under both search-vector and search-access-path tokens → register status reader, capability reader, schema-maintenance scheduler → construct the remediation executor with the core table repository + reconciler → register the maintenance projection as a Singleton.
**Invariant:** metaDb is mandatory; dataDb may equal metaDb (single-DB deployments); the same reconciler instance is exposed under two tokens so both search-vector and search-access-path callers share one lifecycle; the executor is constructed with the core `ITableRepository` so it can resolve `Table` objects for schema maintenance.
**Probe:** exercised by every DB-backed spec that calls `registerV2TableOpsPostgresAdapter`; no dedicated unit spec for the wiring itself.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "registerV2TableOpsPostgresAdapter v2TableOpsPostgresTokens PostgresTableSearchVectorReconciler", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the meta/data dual-DB resolution with dataDb→metaDb fallback, one-reconciler-two-tokens sharing, and executor construction with the core repository; adapt token names and container API to host; omit teable's specific token symbols if the host uses a different DI. Coverage: fully indexed.
