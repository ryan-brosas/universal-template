<!-- capsule-v2 -->
# Boot permission reflection — how does a container with a read-only DB user get gracefully degraded instead of crash-looping?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Which pg privilege check runs at startup, and what env flag flips when it fails?

## has_database_privilege probe → env-flag degradation
**Path/Symbol:** `packages/nocodb/src/helpers/initBaseBehaviour.ts:initBaseBehavior` (whole 89L); called from `src/providers/init-meta-service.provider.ts:167` AFTER upgrader + plugin init.
**Signature:** `initBaseBehavior(): Promise<void>`; inner `isSchemaCreateAllowed(tempConnection, dataConfig, skipDatabaseCreation = false)`.
**Data Shape:** pg-only reflection `SELECT has_database_privilege(:user, :database, 'CREATE')`; toggle = NC_DISABLE_PG_DATA_REFLECTION ('true'/'false').

### Decisive source
```ts
if (!schemaCreateAllowed?.rows?.[0]?.has_database_privilege) {
  // set NC_DISABLE_PG_DATA_REFLECTION to true and log warning
  process.env.NC_DISABLE_PG_DATA_REFLECTION = 'true';
  logger.warn(`User ${...user} does not have permission to create schema, minimal databases feature will be disabled`);
  return;
}
// set NC_DISABLE_PG_DATA_REFLECTION to false
process.env.NC_DISABLE_PG_DATA_REFLECTION = 'false';
```
(:67–:79)

**Flow:** boot sequence reaches initBaseBehavior only for pg data sources (other clients return; NC_DISABLE_PG_DATA_REFLECTION=true short-circuits) → open THROWAWAY CustomKnex connection → probe CREATE privilege, recursing once through createDatabaseIfNotExists when the error is "database does not exist" and creation wasn't yet attempted → on missing privilege or ANY probe error: set the disable flag + warn (never throw) → finally destroy the temp connection.
**Invariant:** the check WRITES ITS RESULT INTO process.env — downstream minimal-databases features read NC_DISABLE_PG_DATA_REFLECTION instead of re-probing, so this must run exactly once before those paths. Failure degrades capability rather than failing boot (a restricted DB user is a supported deployment). The temp connection is destroyed in finally even though it's also used by the recursive create attempt.
**Probe:** `cd packages/nocodb && grep -c "has_database_privilege" src/helpers/initBaseBehaviour.ts` (=2: SQL + result read) and `grep -c "NC_DISABLE_PG_DATA_REFLECTION" src/helpers/initBaseBehaviour.ts` (=7 incl comments) and `grep -c "createDatabaseIfNotExists" src/helpers/initBaseBehaviour.ts` (=1).
**Direct test:** none upstream — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "initBaseBehavior has_database_privilege NC_DISABLE_PG_DATA_REFLECTION", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt boot-time privilege reflection that downgrades via a documented flag instead of crashing; adapt the SQL to your dialect's ACL introspection; omit if all deployments run privileged users. Coverage caveat: grep-pinned only.
