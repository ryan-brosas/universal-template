<!-- capsule-v2 -->
|# Search-path grandfathering migration — pinning old behavior INTO rows so a merge fix never flips live sources

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** When a bugfix changes effective config resolution, how do you backfill EXISTING rows so they keep old behavior while new rows get the fixed behavior — across a paged scan without clobbering concurrent writes?

## Path/Symbol
`packages/nocodb/src/modules/jobs/migration-jobs/nc_job_015_pg_source_searchpath_backfill.ts:grandfatherSearchPath` (43–61), `.job` (76–233); mechanism twins presence-gated-override.md + connection-reset-protocol.md + ncmeta-now-contract.md.

**Signature:** `grandfatherSearchPath(source: Source): string[] | null` (null = leave untouched); `job(): Promise<boolean>`.

**Data Shape:** candidates = external pg/mssql sources (NOT meta/local/deleted) with `fk_integration_id IS NOT NULL`. Decision returns `[defaultSchema]` ('public' pg / 'dbo' mssql) written into the SOURCE config where it wins the getConfig merge.

### Decisive source
```ts
// pure decision fn: null means "no change" for FOUR distinct reasons
export function grandfatherSearchPath(source: Source): string[] | null {
  if ((source.type !== 'pg' && source.type !== 'mssql') || source.isMeta()) return null;
  const ownConfig = source.getSourceConfig();          // pre-merge view
  if (ownConfig?.searchPath?.length) return null;      // already pinned → idempotent re-run
  const defaultSchema = source.type === 'mssql' ? 'dbo' : 'public';
  const effectiveSchema = source.getConfig()?.searchPath?.[0]; // post-fix merged view
  if (!effectiveSchema || effectiveSchema === defaultSchema) return null;
  return [defaultSchema];                              // pin to PRE-fix behavior
}
```

**Flow:** `startedAt = ncMeta.now()` → count candidates (same filter) → keyset walk (500/page, LEFT JOIN integration_config, hydrate `new Source(row)`) → decision fn per row → `Source.update({config: {...own, searchPath}})` → **`NcConnectionMgrv2.resetSource(source)`** → audit log; per-row try/catch continues.

**Invariant:** (1) Grandfathering writes the OLD behavior INTO the row — never special-case the reader. (2) Four-way null contract keeps re-runs no-ops and scope tight. (3) `created_at < startedAt` bounds the mid-run creation race (random nanoid ids can land new rows in unvisited pages; pinning fresh user config to public would destroy it). (4) update-then-resetSource is MANDATORY: Source.update bumps only the Redis version — without resetSource the running instance serves its stale local connection forever (its synced version already equals the bump, staleness never fires locally). (5) SQL filter mirrors the in-memory guard (is_meta/is_local/deleted ⇔ isMeta()); filter and guard must agree.

**Probe:** no unit test upstream. Source-grounded probe: header comment 8–29 (why pinning beats letting the fix flip schemas), :69-74 (keyset rationale), :88-93 (dialect date-binding), :184-207 (update+reset pairing comment verbatim), pairing capsules keyset-backfill-walk.md / ncmeta-now-contract.md / connection-reset-protocol.md / presence-gated-override.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "grandfatherSearchPath PgSourceSearchPathBackfillMigration startedAt resetSource", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the pure four-null decision fn, keyset+race-bound scan, and update-then-reset pairing; adapt config keys/dialects/default-schema names; omit pg/mssql specifics unless porting source-config merging. Coverage caveat: no in-repo unit tests; source-grounded.
