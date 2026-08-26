<!-- capsule-v2 -->
# cross-base cache invalidation — why does a rename in base B never reach base A's compiled-query cache without a workspace-wide sweep?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Base-scoped discovery can't see referrers in OTHER bases — what extra pass closes that gap, and under which context must those invalidations run?

## cross-base cache invalidation
**Path/Symbol:** `packages/nocodb/src/helpers/singleQueryCacheInvalidator.ts` — `clearCrossBaseReferringModels` (:386–460), called from the table-rename path (:103–108, empty seed) and column-rename path (:178–183, seeded with the renamed column id).
**Signature:** `clearCrossBaseReferringModels(context, changedModelId, seedColumnIds: Set<string>, ncMeta?) → Promise<void>`.
**Data Shape:** inbound cross-base links found by raw knex on COL_RELATIONS: `.where('fk_workspace_id', ctx.workspace_id).whereNot('base_id', ctx.base_id).where('fk_related_base_id', ctx.base_id).where('fk_related_model_id', changedModelId)` — mirrors `Base.cleanupCrossBaseLinksInto`.

### Decisive source
```ts
// :372–383 (comment verbatim):
// Inbound cross-base relations span bases, so they are read workspace-wide via
// knex ... For each referring base we rebuild the transitive embedding-column
// closure IN THAT BASE and invalidate its models USING THAT BASE'S context —
// invalidating with the changed model's context would scope the cache keys to
// the wrong base and silently no-op.
// :418–450 core loop:
for (const [refBaseId, linkColIds] of linkColsByBase) {
  try {
    const refCtx: NcContext = { ...context, base_id: refBaseId };
    const embeddingColumnIds = new Set<string>([
      ...seedColumnIds,
      ...linkColIds,
    ]);
    const { lookups, rollups } = await loadBaseLookupsAndRollups(refCtx, ncMeta);
    expandEmbeddingColumns(embeddingColumnIds, lookups, rollups, linkColIds);
    const referringModelIds = await resolveModelIdsFromColumnIds(
      refCtx, [...embeddingColumnIds], ncMeta,
    );
    if (referringModelIds.size) {
      await invalidateSingleQueryCacheForModels(refCtx, [...referringModelIds], ncMeta);
    }
  } catch (e) { logger.error(...); }   // per-base best-effort
}
```

**Flow:** read inbound cross-base relations workspace-wide (raw knex because metaList2 is base-scoped) → group link columns by their LIVING base → per base: rebuild context with THAT base_id, seed with the cross-base link columns (+ caller-provided changed-column ids), re-run the SAME transitive closure within that base, invalidate using that base's context.
**Invariant:** (1) Cache keys are base-scoped — invalidating with the CHANGED model's context silently no-ops for other bases' models; every query AND the final invalidation must use refCtx. (2) Best-effort contract (:419–423): this runs AFTER the rename committed, outside any transaction; a failure must log-and-continue to the next base, never throw past realtime broadcast/hooks and 500 a successful rename — "a missed invalidation degrades to stale cache, not a failed rename." (3) The initial knex read itself is try/catch'd to a silent return (:402–405).
**Probe:** `grep -c "where('fk_related_base_id', context.base_id)" packages/nocodb/src/helpers/singleQueryCacheInvalidator.ts` → `1`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "clearCrossBaseReferringModels fk_related_base_id", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-referring-base context swap and swallow-don't-throw error policy as one inseparable unit; adapt MetaTable/knex idioms; omit nothing here — both halves are the port.
