<!-- capsule-v2 -->
# Boot-failure version ratchet — how does the meta provider refuse dangerous upgrades BEFORE touching data, and in what order do the init steps run?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Which checks gate NcUpgrader, and why must admin/env/encryption init precede it?

## Ordered factory with pre-flight version gates
**Path/Symbol:** `packages/nocodb/src/providers/init-meta-service.provider.ts:InitMetaServiceProvider` (whole 180L; gates :53–100, ordering :117–174).
**Signature:** FactoryProvider.useFactory(eventEmitter, appHooksService) → MetaService (the provider IS boot).
**Data Shape:** NC_VERSION='0258003'; NC_MIGRATION_JOBS_VERSION='14'; gate threshold: config.version < 100002 → refuse.

### Decisive source
```ts
if (+configObj.version < 100002) {
  throw new Error(
    `You are trying to upgrade from an old version of NocoDB. Please upgrade to 0.207.3 first and then you can upgrade to the latest version.`);
}
} else {
  // if bases are present then it is an old version missing the config
  const isOld = (await metaService.legacyProjectList())?.length;
  if (isOld) { throw new Error(`You are trying to upgrade from an old version ...`); }
}
...
Noco.firstEeLoad = isEE && !v0TableExists && v2TableExists && !v3TableExists;
```
(:74–:87, :99–:100)

**Flow:** prepareEnv → NcConfig → cache init → MetaService; THEN pre-flight: read NC_CONFIG_MAIN — if present and version < 100002 THROW (upgrade-to-0.207.3-first); if absent but legacy projects exist, same throw (old install missing config row) → detect migration-table generation trio (xc_knex_migrationsv0/v2/v3) to compute firstEeLoad → metaService.init() + wire Noco statics → fresh installs bump migration-jobs state to current → initJwt → **initAdminFromEnv** → loadEEState → cloud plugin population (NC_LICENSE_KEY) → **NcUpgrader.upgrade** → NcPluginMgrv2.init → T.init + app-started event → **initBaseBehavior** → **initDataSourceEncryption** → verifyDefaultWorkspace.
**Invariant:** the version gates MUST run before any migration touches data — refusing early turns a destructive cross-version jump into a clean error message. Admin-from-env precedes the upgrader so migrations can assume the super user exists; encryption backfill runs AFTER the upgrader so new columns exist. firstEeLoad's three-table probe distinguishes a genuine first EE load from reinstalls. Cloud-only failures rethrow when NC_CLOUD==='true' but log-and-continue otherwise.
**Probe:** `cd packages/nocodb && grep -c "upgrade to 0.207.3" src/providers/init-meta-service.provider.ts` (=2 both gates) and `grep -c "NC_VERSION\|NC_MIGRATION_JOBS_VERSION" src/providers/init-meta-service.provider.ts` (=4).
**Direct test:** none upstream for this provider — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "InitMetaServiceProvider NcUpgrader upgrade firstEeLoad NC_CONFIG_MAIN", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fail-fast version gates + explicit boot-step ordering with rationale; adapt thresholds/version names; omit if your migrator self-guards. Coverage caveat: grep-pinned only.
