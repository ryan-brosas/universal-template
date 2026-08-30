<!-- capsule-v2 -->
# Search-vector executor ownership & rewrite guards — what invariants keep a managed generated-column + GIN index from destroying user data?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Creating a STORED generated column rewrites the whole table and DROPping one can destroy data. What guards does teable layer so a hand-built or stale payload can never rewrite/drop a real user column or index, and a large table can't be rewritten silently?

## Managed-name assertion + advisory-lock + large-rewrite permission + cleanup-on-failure
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/searchVector.ts` — `PostgresTableSearchVectorExecutor.execute` (853–876), `.executeUnlocked` (878–999), `assertManagedSearchVectorNames` (2338–2352), `assertTableRewriteAllowed` (1022–1037), `assertDefinitionChangeAllowed` (1009–1020), `createManagedObjects` (1176–1210), `dropManagedObjects` (1148–1162), `rethrowAfterManagedObjectCleanup` (1121–1147), `upsertConfig` (1244–1328).
**Signature:** `execute(input: ExecuteTableSearchVectorInput): Promise<ExecuteTableSearchVectorResult>`; result = `{action:'created'|'rebuilt'|'verified', createdOrVerified, candidateKey, generatedColumnName, indexName, provider, operatorClass, languageConfig, fieldIds[], fieldDbNames[], estimatedRows, inventory, planEvidence?}`.
**Data Shape:** payload = `{candidateKey, languageConfig, searchProbe?, validationMode:'plan'|'real_ddl', generatedColumnName, indexName, provider?, operatorClass?, fields[{fieldId, fieldDbName, fieldType?}], searchScope?, allowLargeTableRewrite?, rebuild?}`.

### Decisive source
```ts
// advisory-lock per table, then re-assert managed names on the UNTRUSTED payload:
await sql`SELECT pg_advisory_lock(hashtext('teable.table_query_ops.search_vector'), hashtext(${tableId}))`.execute(lockedMetaDb);
try { return await new PostgresTableSearchVectorExecutor(lockedMetaDb, lockedDataDb).executeUnlocked(input); }
finally { await sql`SELECT pg_advisory_unlock(...)`.execute(lockedMetaDb); }
// executeUnlocked FIRST:
assertManagedSearchVectorNames(columnName, indexName); // column must start __tqops_search_ (or legacy __tqops_tsv_); index idx_tqops_search_ (or idx_tqops_tsv_)
// large/unknown table rewrite gate:
const requiresPermission = !alreadyReady && (!rowEstimate.known || rowEstimate.rows >= LARGE_TABLE_REWRITE_ESTIMATED_ROWS /* 50_000 */);
if (!requiresPermission || input.payload.allowLargeTableRewrite) return;
throw new Error(rowEstimate.known ? `...may rewrite a large table (${rows} estimated rows); rerun with allowLargeTableRewrite=true`
                                   : `...requires a full table rewrite but the table size is unknown (never analyzed); run ANALYZE first or rerun with allowLargeTableRewrite=true`);
// create: generated STORED column + COMMENT marker + CONCURRENTLY GIN index
`ALTER TABLE ${tableSql} ADD COLUMN IF NOT EXISTS ${col} text GENERATED ALWAYS AS (${expression}) STORED`
`COMMENT ON COLUMN ${tableSql}.${col} IS ${quoteLiteral(buildSearchDocumentDefinitionMarker(expression, providerCapability))}`
`CREATE INDEX CONCURRENTLY IF NOT EXISTS ${idx} ON ${tableSql} USING GIN (${col} ${qualifyOperatorClass(providerCapability)})`
```

**Flow:** `execute` takes a per-table advisory lock → `executeUnlocked` re-asserts managed names on the payload, reads the row estimate (`reltuples`, `known=false` when `<0`), resolves the provider capability (must be usable), validates real-DDL requires a `searchProbe` ≥ min-probe-length, re-derives the current config and asserts no definition change without `rebuild`, inspects the live inventory, asserts it's applicable (stale/invalid requires `rebuild`), computes `alreadyReady`, gates large/unknown rewrites, optionally marks the old config `rebuild_pending`, then `createAndValidateManagedObjects` (drop-then-create on rebuild; re-inspect; real-DDL plan validation must show cost improvement + ILIKE compatibility) → `upsertConfig` (marks sibling candidate keys `stale`, upserts the active row) → returns `action`. On any error after objects changed, `rethrowAfterManagedObjectCleanup` drops them.
**Invariant:** the executor may ONLY create/drop objects whose names pass `assertManagedSearchVectorNames`; a large (≥50k est.) or unknown-size table rewrite requires explicit `allowLargeTableRewrite`; a definition change (candidateKey) requires `rebuild`; stale/invalid inventory requires `rebuild`; real-DDL validation must prove the index is used AND cost improves AND ILIKE results are preserved, else the objects are rolled back.
**Probe:** `searchVector.lifecycle.db.spec.ts` (491L) drives create/rebuild/drop against a real DB; `searchVector.spec.ts:73` 'rejects hand-built payloads that do not match advisor field coverage' pins the name/coverage guard.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableSearchVectorExecutor assertManagedSearchVectorNames assertTableRewriteAllowed createManagedObjects", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the advisory-lock serialization, managed-name ownership assertion, large/unknown-rewrite permission gate, definition-change and stale-inventory rebuild requirements, and cleanup-on-failure; adapt prefixes, lock-key namespace, and rewrite threshold to host; omit the pg_bigm/pg_trgm operator-class specifics. Coverage caveat: `searchVector.ts` is parse_partial at a few template-literal lines (outside cited ranges); the guard logic is fully indexed.
