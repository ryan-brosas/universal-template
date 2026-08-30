<!-- capsule-v2 -->
# Query-ops schema bootstrap — how does teable provision its five meta tables idempotently and keep them forward-compatible?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** The query-ops adapter needs its own meta tables (observation windows, recommendations, tasks, leases, search-vector config) created before first use, and later columns added without breaking existing installs. What's the idempotent DDL pattern?

## IF NOT EXISTS tables + partial unique indexes + IF NOT EXISTS column backfills
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/schema.ts` — `ensureTableQueryOpsSchema` (91–248), `TableQueryOpsDatabase` type (6–89).
**Signature:** `ensureTableQueryOpsSchema(db): Promise<void>`.
**Data Shape:** five tables — `table_query_observation_window` (id PK, base_id/table_id NOT NULL, shape_hash, window_start, counters, shape jsonb, sql_diagnostics jsonb), `table_query_recommendation` (open-partial unique on table_id/shape_hash/policy_version), `table_query_remediation_task` (status/kind/created_time index, attempts/max_attempts/locked_at/locked_by/last_error), `table_query_ops_lease` (lease_key PK, owner_id, expires_at, updated_time), `table_query_search_vector_config` (unique on table_id/candidate_key, status, last_inspection jsonb, search_scope/semantics/access_path/provider/operator_class/language_config).

### Decisive source
```ts
await db.schema.createTable('table_query_observation_window').ifNotExists()
  .addColumn('id','text',c=>c.primaryKey()).addColumn('base_id','text',c=>c.notNull()) ... .execute();
// forward-compat: add later columns IF NOT EXISTS (raw SQL for ones the builder can't express):
await sql`ALTER TABLE table_query_observation_window ADD COLUMN IF NOT EXISTS sql_diagnostics jsonb`.execute(db);
await sql`ALTER TABLE table_query_search_vector_config
  ADD COLUMN IF NOT EXISTS semantics text NOT NULL DEFAULT 'lexical',
  ADD COLUMN IF NOT EXISTS access_path text NOT NULL DEFAULT 'generated_tsvector',
  ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'tsvector',
  ADD COLUMN IF NOT EXISTS operator_class text`.execute(db);
// partial unique index for open recommendations:
await sql`CREATE UNIQUE INDEX IF NOT EXISTS table_query_recommendation_open_unique_idx
  ON table_query_recommendation (table_id, shape_hash, policy_version) WHERE status='open'`.execute(db);
```

**Flow:** create each table with `.ifNotExists()` and `NOT NULL` on identity columns → add later-evolved columns via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (raw SQL where the Kysely builder can't express `IF NOT EXISTS` on a column) → create plain and partial-unique indexes with `IF NOT EXISTS`. `register.ts` calls this when `ensureSchema:true`.
**Invariant:** every statement is idempotent (IF NOT EXISTS on tables, columns, and indexes) so re-running the adapter on an existing install is a no-op; identity columns are NOT NULL; the open-recommendation uniqueness is a PARTIAL index (only `status='open'`), which the repository's upsert relies on.
**Probe:** no dedicated unit spec (DDL bootstrap); exercised by every DB-backed spec that calls `registerV2TableOpsPostgresAdapter({ensureSchema:true})`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ensureTableQueryOpsSchema TableQueryOpsDatabase table_query_search_vector_config", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt idempotent IF NOT EXISTS table/column/index bootstrap with partial-unique indexes and raw-SQL column backfills; adapt table names, columns, and defaults to host; omit teable's search-vector config columns if the host has no managed search index. Coverage: fully indexed.
