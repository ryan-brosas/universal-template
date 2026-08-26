<!-- capsule-v2 -->
# Filter.redisPostInsert — one row, up to five list-cache memberships

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory project `nocodb`. **Question:** When porting the filter write path, which list caches must a new FILTER_EXP row be appended to, and what must happen to dependent caches afterward?

## Cache fan-out + single-query invalidation
**Path/Symbol:** `packages/nocodb/src/models/Filter.ts:Filter.redisPostInsert` (:267-444); scope enum `packages/nocodb/src/utils/globals.ts:FilterCacheScope` (:687-697).
**Signature:** `static async redisPostInsert(context: NcContext, id, filter: Partial<FilterType>, ncMeta = Noco.ncMeta)`.
**Data Shape:** key = `FILTER_EXP:<id>`; list memberships keyed by present FKs: `[VIEW, fk_view_id]`, `[HOOK, fk_hook_id]`, `[PARENT_COLUMN, fk_parent_column_id]`, `[COLUMN, fk_column_id]`, `[RLS_POLICY, fk_rls_policy_id]`, `[BUTTON_COLUMN, fk_button_col_id]`; parent-scoped twins `[VIEW|HOOK|PARENT_COLUMN, <scope-id>, fk_parent_id]` + always `[PARENT, fk_parent_id]` when nested.

### Decisive source
```ts
// packages/nocodb/src/models/Filter.ts:273-286 — admission gate (400, not silent)
if (!(id && (filter.fk_view_id || filter.fk_hook_id ||
    filter.fk_parent_column_id || filter.fk_level_id ||
    filter.fk_button_col_id))) {
  NcError.get(context).badRequest(
    `Mandatory fields missing in FILTER_EXP cache population : ...`);
}
// :424-441 — after caching, view filters must kill the optimized single-query cache
{
  // if not a view filter then no need to delete
  if (filter.fk_view_id) {
    const view = await View.get(context, filter.fk_view_id, false, ncMeta);
    // View may be missing if it was deleted concurrently or the filter
    // is orphaned — skip cache invalidation rather than throwing.
    if (view) {
      await View.clearSingleQueryCache(context, view.fk_model_id, [view], ncMeta);
    }
  }
}
```

**Flow:** gate on id + at least one primary scope → read-through get of the row object → set under `FILTER_EXP:<id>` → parallel `appendToList` for EVERY applicable scope (root-level and parent-nested twins; `[PARENT, id]` unconditionally for children) → finally, if view-filter, `View.clearSingleQueryCache(modelId, [view])`.
**Invariant:** a filter row cached under `FILTER_EXP:<id>` but absent from its scope lists is unreachable by every reader (`getList` mgets members from the list keys) — membership writes are not optional; HookFilter's twin appends to only 3 lists because hook-filters have exactly one scope family. The single-query cache must be invalidated on ANY filter mutation of a view or stale reads persist.
**Probe:** No direct unit test at this pin. Deterministic probes: verbatim grep `Mandatory fields missing in FILTER_EXP cache population` hits Filter.ts:284 AND the HookFilter twin's logger.error variant (HookFilter.ts:114 — same sentence, different reaction: 500 vs 400); `search_graph --project nocodb --query 'redisPostInsert FILTER_EXP'` resolves both twins line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "redisPostInsert appendToList FilterCacheScope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: multi-membership cache registration derived from the row's own FKs, unconditional PARENT-list entry for nested rows, mandatory-scope admission gate, and post-write single-query invalidation with a concurrent-delete null-view guard (skip, don't throw). Adapt scope names/twins to your host's surfaces. Omit nothing portable. Coverage caveat: deterministic probes only at this pin.
