<!-- capsule-v2 -->
|# Connection-reset protocol — delete-ref-then-bump-and-sync, and why Source.update deliberately does neither

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** After changing a source's connection config, how do you invalidate cached knex connections on THIS server AND all others — and which callers may skip the local teardown?

## Path/Symbol
`packages/nocodb/src/utils/common/NcConnectionMgrv2.ts:resetSource` (77–80), `bumpSourceVersion` (68–70), `deleteConnectionRef` (61–63), `checkSourceStaleness` (87–95), `get` (127+); the deliberate non-resetter `models/Source.ts:229-234`.

**Signature:** `static async resetSource(source: SourceIdentity)`; `bumpSourceVersion(source)`; `checkStaleness(key, onDestroy)`.

**Data Shape:** two primitives — a local connection-refs map (asyncDelete by connectionKey) and a Redis version tracker per key (bumpAndSync = write new version AND sync local copy). `get()` consults staleness BEFORE returning cached connections.

### Decisive source
```ts
// Delete ref first, then bump-and-sync so that concurrent get() calls on
// this server create a fresh connection without re-triggering staleness.
public static async resetSource(source) {
  await this.deleteConnectionRef(source);
  await this.sourceVersionTracker.bumpAndSync(this.connectionKey(source));
}
// models/Source.ts — why update() does NOT call reset:
// Bump Redis version so other servers invalidate on next read.
// Don't destroy the local connection — Source.update() is also called
// for metadata-only changes (readonly flags, alias, order). Callers that
// change connection config (integrations service, sourceCleanup) call
// resetSource() directly.
await NcConnectionMgrv2.bumpSourceVersion(oldSource);
```

**Flow:** config-changing caller → resetSource: drop LOCAL ref (next get() rebuilds from new config) → bumpAndSync (other servers detect version mismatch in checkSourceStaleness on their next get() and destroy their own refs). Metadata-only callers → bumpSourceVersion only: locals keep serving; remote servers still invalidate harmlessly.

**Invariant:** (1) ORDER is load-bearing: delete the local ref BEFORE bumping — since bumpAndSync also syncs the local copy, reversing the order would leave this server's next get() believing its (stale) connection fresh. (2) Staleness is LAZY (checked at get(), not pushed): invalidation latency = time to next connection acquisition. (3) The update/reset split is a documented caller contract: change CONNECTION config through Source.update ⇒ YOU call resetSource (nc_job_015 does exactly this after pinning searchPath). (4) The same tracker stashes db major version onto knex client config for dialect-aware paths.

**Probe:** no unit test upstream. Source-grounded probe: NcConnectionMgrv2.ts:73-80 + 84-86 comments verbatim, :127-131 (staleness inside get), Source.ts:229-234 comment, consumer nc_job_015:198-207 ("its own comment says config changing callers must resetSource() themselves").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "NcConnectionMgrv2 resetSource bumpSourceVersion checkSourceStaleness deleteConnectionRef", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt delete-ref-then-bump-and-sync ordering, lazy staleness checks, and the update-vs-reset caller contract; adapt cache/redis clients; omit the mysql BIT/decimal typeCast plumbing unless porting mysql. Coverage caveat: no in-repo unit tests; source-grounded.
