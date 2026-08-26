<!-- capsule-v2 -->
# Search-vector generated-column lifecycle — how does teable keep a substring-search access path (generated column + GIN index) reconciled with a live table?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a self-managing full-text/substring search index get created, validated against the planner, rebuilt on schema change, and safely dropped without ever touching a real user column?

## Advisor → Executor → Reconciler over a managed generated column
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/searchVector.ts` — `PostgresTableSearchVectorAdvisor.analyze` (524–647), `PostgresTableSearchVectorExecutor.execute` (853–876) + `.executeUnlocked` (878–999), `PostgresTableSearchVectorReconciler.reconcile` (1337–1423) + `.maintainAfterSchemaChange` (1425–1498).
**Signature:** `analyze(input: AnalyzeTableSearchVectorInput): Promise<AnalyzeTableSearchVectorResult>`; `execute(input: ExecuteTableSearchVectorInput): Promise<ExecuteTableSearchVectorResult>`; `reconcile(ctx, input: ReconcileTableSearchVectorInput): Promise<Result<ReconcileTableSearchVectorResult, DomainError>>`.
**Data Shape:** advisor returns `{recommendations[], inventory, coverageReport, scopeHeatReport?, scopedExpressionRecommendations[]}`; a recommendation carries `candidateKey, generatedColumnName, indexName, provider ('pg_bigm'|'pg_trgm'), operatorClass, coveredFields[], searchScope, languageConfig`. Executor payload must carry the exact advisor names; the config row `table_query_search_vector_config` stores `candidate_key, generated_column_name, index_name, provider, operator_class, field_ids, field_db_names, search_scope, status ('ready'|'stale'|'rebuild_pending'), last_inspection`.

### Decisive source
```ts
// Executor: ownership guard + advisory-lock serialization + managed-name assertion
await sql`SELECT pg_advisory_lock(hashtext('teable.table_query_ops.search_vector'), hashtext(${tableId}))`.execute(lockedMetaDb);
try { return await new PostgresTableSearchVectorExecutor(lockedMetaDb, lockedDataDb).executeUnlocked(input); }
finally { await sql`SELECT pg_advisory_unlock(...)`.execute(lockedMetaDb); }
// executeUnlocked — only ADD/DROP objects the advisor owns
assertManagedSearchVectorNames(columnName, indexName);   // prefix __tqops_search_ / idx_tqops_search_
// createManagedObjects — generated STORED column + GIN index, both CONCURRENTLY-safe
`ALTER TABLE ${tableSql} ADD COLUMN IF NOT EXISTS ${col} text GENERATED ALWAYS AS (${expression}) STORED`
`CREATE INDEX CONCURRENTLY IF NOT EXISTS ${idx} ON ${tableSql} USING GIN (${col} ${operatorClass})`
```
**Flow:** `reconcile` → `advisor.analyze` (reads row estimate, table size, existing inventory, runs EXPLAIN before/after a **hypothetical** HypoPG index to validate the plan) → pick recommendation → `assertSearchVectorExecutionCandidate` (real-DDL mode) or `assertReadySearchVectorExecutionRecommendation` (plan mode) → `executor.execute` (advisory-lock per table, re-assert managed names, `assertDefinitionChangeAllowed` if candidateKey changed, `assertTableRewriteAllowed` for large/unknown tables unless `allowLargeTableRewrite`, create generated column + GIN index, re-inspect inventory, upsert config) → return `{action:'created'|'verified'|'rebuilt'}`. On any error after managed objects changed, `rethrowAfterManagedObjectCleanup` drops them so a failed validation never leaves a half-built index. `maintainAfterSchemaChange` re-analyzes with the stored config, computes `rebuild = candidateKey changed || inventory not ready`, and re-executes with `allowLargeTableRewrite:false` (large tables stay pending for admin approval).
**Invariant:** the executor may ONLY create/drop objects whose names pass `assertManagedSearchVectorNames` (the `__tqops_search_` / `idx_tqops_search_` prefixes) — a hand-built payload can never target a real user column or index; a large/unknown table rewrite is gated behind explicit permission; HypoPG GIN-unsupported degrades to explain-only (keeps `needs_plan_validation`) rather than failing; every validation failure cleans up its managed objects.
**Probe:** `packages/v2/adapter-table-query-ops-postgres/src/searchVector.spec.ts::"accepts the exact ready advisor recommendation"` (:15), `::"rejects hand-built payloads that do not match advisor field coverage"` (:73); `searchVector.lifecycle.db.spec.ts` (491L) pins the create/rebuild/drop lifecycle against a real DB.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableSearchVectorAdvisor analyze PostgresTableSearchVectorExecutor execute", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-phase advisor→executor→reconciler shape with a managed generated column + GIN index, advisory-lock serialization, HypoPG hypothetical-index plan validation, managed-name ownership guard, large-table rewrite permission gate, and cleanup-on-failure. Adapt the name prefixes, lock key namespace, provider capability probing, and config table schema. Omit teable's provider-capability probing (pg_bigm/pg_trgm cluster requirements) and scope-heat recommendation unless building substring search. Caveat: `searchVector.ts` is parse_partial at a few template-literal lines (outside cited ranges); coverage otherwise matches HEAD.
