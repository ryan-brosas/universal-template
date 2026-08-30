<!-- capsule-v2 -->
# NcUpgrader version ratchet — how do app-level migrations run once each under ONE meta transaction, and what makes the version comparison string-based?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does the upgrader decide WHICH upgraders to run on an existing install, and what is the crash-consistency story?

## NC_CONFIG_MAIN store row + per-step version commit
**Path/Symbol:** `packages/nocodb/src/version-upgrader/NcUpgrader.ts:NcUpgrader.upgrade/getUpgraderList` (:31–:150 whole file 169L).
**Signature:** `static async upgrade(ctx: NcUpgraderCtx)`; list entries `{name: '0100002', handler}` — zero-padded `0MMVVVP` strings compared with `>` lexicographically against `process.env.NC_VERSION`.
**Data Shape:** store row key `NC_CONFIG_MAIN` value `{version}` in `MetaTable.STORE` under RootScopes.ROOT/ROOT.

### Decisive source
```ts
ctx.ncMeta = await ctx.ncMeta.startTransaction();
if (!(await ctx.ncMeta.knexConnection?.schema?.hasTable?.(MetaTable.STORE))) return; // fresh DB → nothing to upgrade
for (const version of NC_VERSIONS) {
  if (version.name > configObj.version) {
    await version?.handler?.(ctx);
    config.version = version.name;
    await ctx.ncMeta.metaUpdate(RootScopes.ROOT, RootScopes.ROOT, MetaTable.STORE,
      { value: JSON.stringify({ version: config.version }) }, { key: NcUpgrader.STORE_KEY });
  }
  if (version.name === process.env.NC_VERSION) break;
}
await ctx.ncMeta.commit();   // rollback(e) in catch + evt emit appMigration:failed
```
(:37–:118 condensed)

**Flow:** open ONE meta transaction over ALL upgraders → fresh-install short-circuit (no STORE table ⇒ skip silently, config row gets inserted at current version in the else branch) → run every upgrader whose name sorts ABOVE stored version, re-writing the store row after EACH so the log records progress within the transaction → early-break at target version → single commit; any throw rolls back EVERYTHING and emits telemetry with from/to + first two stack lines via boxen help banner.
**Invariant:** string compare works ONLY because names are zero-padded fixed-width — adding `'9999'` or unpadded names breaks ordering silently. The per-step metaUpdate is intentional: it gives forward progress visibility even though a crash rolls back (the transaction, not the row writes, is the consistency boundary). Upgraders receive `ctx.ncMeta` INSIDE the transaction — they must never open their own meta connections.
**Probe:** `cd packages/nocodb && grep -n "STORE_KEY = " src/version-upgrader/NcUpgrader.ts` (:28 `'NC_CONFIG_MAIN'`) and `grep -c "{ name: '01\\|{ name: '02" src/version-upgrader/NcUpgrader.ts` (=13 registered upgraders).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "NcUpgrader getUpgraderList NC_CONFIG_MAIN startTransaction metaUpdate version.name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the transactional all-or-nothing wrapper + zero-padded name discipline; adapt store table/version source; omit the boxen banner. Distinct from nc_jobs migration-jobs (per-job lock+requeue — separate plane): THIS is the boot-time app-version path. Coverage caveat: no spec; count-pinned greps.
