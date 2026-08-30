<!-- capsule-v2 -->
# Per-(view,role) visibility cache — how is view-level role ACL cached and evicted without orphaned list members?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What does a minimal per-pair ACL model look like — key shape, list membership, delete fan-out, and the base-cascade reuse rule?

## ModelRoleVisibility
**Path/Symbol:** `packages/nocodb/src/models/ModelRoleVisibility.ts` WHOLE (223L) — `list` (:28-54), `get/update/delete` (:56-155), `deleteByBaseId` (:157-175), `insert` (:177-222).
**Signature:** keyed pair `(fk_view_id, role)` → row `{disabled: boolean}`; object-cache key `${MODEL_ROLE_VISIBILITY}:${fk_view_id}:${role}`; list cache scoped `[baseId]` with projected child keys `['fk_view_id','role']`.
**Data Shape:** Table MODEL_ROLE_VISIBILITY; note fk_model_id is COMMENTED OUT in both class and get() query — visibility is VIEW-scoped, not model-scoped, at this pin.

### Decisive source
```ts
static async delete(context: NcContext, fk_view_id: string, role: string, ncMeta = Noco.ncMeta) {
  const res = await ncMeta.metaDelete(context.workspace_id, context.base_id, MetaTable.MODEL_ROLE_VISIBILITY, { fk_view_id, role });
  await NocoCache.deepDel(context, `${CacheScope.MODEL_ROLE_VISIBILITY}:${fk_view_id}:${role}`, CacheDelDirection.CHILD_TO_PARENT);
  return res;
}
static async deleteByBaseId(context: NcContext, baseId: string, ncMeta = Noco.ncMeta) {
  const rows = await ncMeta.metaList2(..., { condition: { base_id: baseId } });
  // reuse the per-row delete so the per-(view,role) cache is evicted
  for (const row of rows) {
    await this.delete(context, row.fk_view_id, row.role, ncMeta);
  }
}
```
insert tail:
```ts
await NocoCache.appendToList(context, CacheScope.MODEL_ROLE_VISIBILITY, [context.base_id], key);
```

**Flow:** insert defaults source_id from the view when absent → metaInsert2 → read-through get() repopulates the pair key → appendToList registers the new key under the base's list so list reads stay coherent → update writes DB then NocoCache.update on the pair key only → delete = metaDelete + deepDel CHILD_TO_PARENT (evicts pair AND prunes every list referencing it) → base cascade deliberately LOOPS the single-row delete instead of a bulk SQL delete precisely so each pair's cache eviction runs.
**Invariant:** Bulk deletes must go through the per-row path when children are list-registered — one raw DELETE would strand keys inside cached lists (the exact failure mode cache-list-selfheal exists to repair). List caching projects child keys to ['fk_view_id','role'] so the cached list stays small and stable across column additions.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `ModelRoleVisibility.list/get/update/delete`; grep confirms exactly one `deleteByBaseId` loop comment 'reuse the per-row delete'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ModelRoleVisibility deepDel appendToList", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pair-keyed ACL caching with CHILD_TO_PARENT deep deletion and per-row cascade reuse. Adapt scope naming to your cache taxonomy. Omit entirely if your ACL lives at a different grain — but keep the cascade-eviction lesson.
