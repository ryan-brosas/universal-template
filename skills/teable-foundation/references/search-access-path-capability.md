<!-- capsule-v2 -->
# Substring-search provider capability probe — how does teable decide pg_bigm vs pg_trgm is usable without ever running CREATE EXTENSION?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** A GIN substring index needs an operator class that may not be installed or may require a cluster restart to preload. How do you probe availability/install/preload/operator-class in one query and map it to a usable state machine?

## One-query capability probe + state ladder
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/searchAccessPathCapability.ts` — `readPostgresSearchAccessPathCapabilities` (70–98), `resolveSearchAccessPathCapability` (47–68), `resolveCapabilityState` (27–45); `searchVector.ts` — `readSubstringSearchCapabilities` (1988–2000), `selectSubstringSearchProvider` (2002–2007), `toSubstringProviderCapability` (1959–1986).
**Signature:** `readPostgresSearchAccessPathCapabilities(db): Promise<ReadonlyArray<TableSearchAccessPathCapability>>`; `selectSubstringSearchProvider(capabilities): 'pg_bigm'|'pg_trgm'`.
**Data Shape:** capability = `{provider, extensionName, operatorClass ('gin_bigm_ops'|'gin_trgm_ops'), operatorClassSchema?, operatorClassInstalled, minimumProbeLength (pg_bigm 2 / pg_trgm 3), state, installed, available, preloaded, reason?}`. State enum: `ready | requires_cluster_restart | requires_database_extension | unavailable`.

### Decisive source
```sql
SELECT requested.name,
       available.name IS NOT NULL AS available,
       installed.extname IS NOT NULL AS installed,
       current_setting('shared_preload_libraries', true) AS shared_preload_libraries,
       operator_class.schema_name AS operator_class_schema
FROM (VALUES ('pg_bigm'), ('pg_trgm')) AS requested(name)
LEFT JOIN pg_available_extensions available ON available.name = requested.name
LEFT JOIN pg_extension installed ON installed.extname = requested.name
LEFT JOIN LATERAL (
  SELECT n.nspname AS schema_name
  FROM pg_opclass opc JOIN pg_namespace n ON n.oid = opc.opcnamespace JOIN pg_am am ON am.oid = opc.opcmethod
  WHERE opc.opcname = CASE requested.name WHEN 'pg_bigm' THEN 'gin_bigm_ops' ELSE 'gin_trgm_ops' END
    AND am.amname = 'gin'
  ORDER BY (n.nspname = ANY(current_schemas(true))) DESC, n.nspname LIMIT 1
) operator_class ON TRUE
```
```ts
// resolveCapabilityState — strict order: available → preloaded → installed → operator-class → ready
if (!row.available) return { state: 'unavailable', reason: `${row.name}_not_available` };
if (!preloaded) return { state: 'requires_cluster_restart', reason: `${row.name}_not_preloaded` };
if (!row.installed) return { state: 'requires_database_extension', reason: `${row.name}_not_installed` };
if (!operatorClassInstalled) return { state: 'unavailable', reason: `${row.name}_operator_class_missing` };
return { state: 'ready' };
// pg_trgm is bundled with PG, so it is always 'preloaded' by convention:
const preloaded = provider === 'pg_trgm' || isPreloaded(row.shared_preload_libraries, row.name);
```

**Flow:** one query returns both providers' rows → `resolveSearchAccessPathCapability` maps each to a capability (pg_trgm hard-coded preloaded, min-probe 3; pg_bigm must be in `shared_preload_libraries`, min-probe 2) → `toSubstringProviderCapability` re-maps state→`usable`/reason → `selectSubstringSearchProvider` prefers pg_bigm ONLY when already usable, else pg_trgm. The adapter never attempts `CREATE EXTENSION` — it consumes only what's installed.
**Invariant:** the probe is a single LEFT-JOIN ladder over catalog views; `pg_bigm`'s cluster-level preload requirement is enforced as a distinct `requires_cluster_restart` state (not just `unavailable`), and the operator-class must exist in a GIN opclass for the provider to be `ready`. Never install an extension from the advisor path.
**Probe:** `searchAccessPathCapability.spec.ts` `describe('resolveSearchAccessPathCapability')` (5–89) — `it.each` pins all five states (ready / requires_cluster_restart / requires_database_extension / unavailable / operator_class_missing); `searchVector.spec.ts:173` `selectSubstringSearchProvider` 'prefers pg_bigm only when it is already usable'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "readPostgresSearchAccessPathCapabilities resolveSearchAccessPathCapability selectSubstringSearchProvider", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-query capability probe with the strict available→preloaded→installed→opclass→ready ladder and the pg_bigm-preferred-but-only-if-usable selection; adapt provider names and operator classes to host; omit the pg_bigm/pg_trgm specifics if the host uses a different n-gram/extension. Coverage: full (plain SQL tags, no parse_partial in cited ranges).
