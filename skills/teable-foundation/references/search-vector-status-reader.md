<!-- capsule-v2 -->
# Search-vector status reader — how does teable report a table's search-vector state without a hard dependency on the config table existing?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** The status reader must return a sensible `disabled` state before the ops schema is even created, and normalize stored provider/access-path/semantics strings. How is that done?

## to_regclass existence guard + last-active-config read + string normalization
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/searchVectorStatus.ts` — `PostgresTableSearchVectorStatusReader.read` (39–76), `parseState` (25–28), `disabledStatus` (32–37), `fieldCount` (30).
**Signature:** `read(ctx, tableId): Promise<Result<TableSearchVectorStatus, DomainError>>`.
**Data Shape:** status = `{tableId, state:'ready'|'rebuild_pending'|'stale'|'disabled'|'unknown', configured:boolean, languageConfig?, semantics:'substring'|'lexical', provider:'pg_bigm'|'pg_trgm'|'tsvector', accessPath:'generated_text'|'generated_tsvector', coveredFieldCount}`.

### Decisive source
```ts
const relation = await sql`SELECT to_regclass('public.table_query_search_vector_config')::text AS relation_name`.execute(this.metaDb);
if (!relation.rows[0]?.relation_name) return ok(disabledStatus(tableId));   // schema not created yet → disabled
const result = await sql`SELECT status, semantics, access_path, provider, language_config, field_ids
  FROM table_query_search_vector_config
  WHERE table_id=${tableId} AND status IN ('ready','rebuild_pending','stale')
  ORDER BY last_modified_time DESC NULLS LAST, created_time DESC LIMIT 1`.execute(this.metaDb);
if (!result.rows[0]) return ok(disabledStatus(tableId));
// normalize stored strings to the closed enum, unknown → fallback:
const state = parseState(row.status);                       // knownStates = ready/rebuild_pending/stale, else 'unknown'
const semantics = row.semantics === 'substring' ? 'substring' : 'lexical';
const provider = row.provider === 'pg_bigm' || row.provider === 'pg_trgm' ? row.provider : 'tsvector';
const accessPath = row.access_path === 'generated_text' ? 'generated_text' : 'generated_tsvector';
```

**Flow:** probe `to_regclass('public.table_query_search_vector_config')` — if the table doesn't exist, return `disabled` (no hard dependency on schema creation) → read the most-recent active config row (ready/rebuild_pending/stale, newest `last_modified_time`) → if none, return `disabled` → normalize each stored string against the closed enum with a safe fallback → return the status with `coveredFieldCount` from `field_ids` array length.
**Invariant:** the reader never throws when the ops schema is absent — it degrades to `disabled`; stored strings are normalized to the closed enum (unknown provider ⇒ `tsvector`, unknown access path ⇒ `generated_tsvector`) so downstream switches are exhaustive; only the newest active config is reported.
**Probe:** no dedicated unit spec (DB-backed); exercised via the status-read path in `searchVector.lifecycle.db.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableSearchVectorStatusReader read disabledStatus parseState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `to_regclass` existence guard + newest-active-config read + closed-enum string normalization; adapt the config table name and enum vocab to host; omit teable's substring provider/access-path coupling if the host uses another scheme. Coverage: fully indexed.
