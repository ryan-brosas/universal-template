<!-- capsule-v2 -->
# Filter.update / Filter.delete — cache writes ride the DB transaction; deletes are guarded, recursive, and always end in single-query invalidation

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory project `nocodb`. **Question:** How do filter update/delete keep the Redis projection and the optimized single-query cache coherent — including when the row is already gone or the tree is malformed?

## Transaction-attached cache update
**Path/Symbol:** `packages/nocodb/src/models/Filter.ts:Filter.update` (:446-509).
**Signature:** `static async update(context: NcContext, id, filter: Partial<Filter>, ncMeta = Noco.ncMeta)`.
**Data Shape:** extractProps allowlist of 12 keys incl. `fk_level_id` (GUI healing of legacy null-level filters), `fk_value_col_id`, `meta`, `order`, `enabled`; meta re-stringified before both writes.

### Decisive source
```ts
// packages/nocodb/src/models/Filter.ts:483-489
ncMeta.knex.attachToTransaction(async () => {
  await NocoCache.update(
    context,
    `${CacheScope.FILTER_EXP}:${id}`,
    updateObj,
  );
});
```
(Contrast HookFilter.update :199-204 — bare `await NocoCache.update(...)`, no transaction attachment.)

## Guarded recursive delete + trailing invalidation
**Path/Symbol:** `packages/nocodb/src/models/Filter.ts:Filter.delete` (:511-551); family variants `deleteAll` (:833-871), `deleteAllByHook` (:873-898), `deleteAllByRlsPolicy` (:900-925), `deleteAllByParentColumn` (:927-952), `deleteAllByButtonColumn` (:1563-1588).
**Data Shape:** delete = get → guard → recursive child-first walk → per-node metaDelete + `deepDel(CHILD_TO_PARENT)` → ONE final `View.clearSingleQueryCache`.

### Decisive source
```ts
// packages/nocodb/src/models/Filter.ts:514-518 — two guards HookFilter lacks
// Guard against deleting an already-removed filter
if (!filter) return;
const deleteRecursively = async (filter: Filter) => {
  if (!filter || filter.id === filter.fk_parent_id) return;   // self-parent cycle brake
```
```ts
// packages/nocodb/src/models/HookFilter.ts:210-212 — twin has neither guard
const deleteRecursively = async (filter: Filter) => {
  if (!filter) return;
```

**Flow (update):** allowlist → meta stringify → `metaUpdate` → attach the cache update to the ACTIVE knex transaction (commit applies cache, rollback drops it) → reload via `get()` → if view-scoped, clear single-query cache. **Flow (delete):** resolve node; missing ⇒ no-op success; recurse children first; delete+evict each node; after the whole tree, invalidate the view's optimized single-query cache once.
**Invariant:** cache mutation must be transactional with the meta mutation wherever the host supports it; deletion must survive double-delete and self-referencing rows (`id === fk_parent_id`) without throwing; the single-query cache is invalidated even for a delete that removed nothing else.
**Probe:** No direct unit test at this pin. Deterministic probes: verbatim grep `attachToTransaction` in Filter.ts (:483) absent from HookFilter.ts; verbatim greps pinning `Guard against deleting an already-removed filter` (:514) and `filter.id === filter.fk_parent_id` (:518); graph resolves all five deleteAll* variants.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "Filter.delete deleteRecursively deepDel CHILD_TO_PARENT", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: transaction-attached cache updates, double-delete idempotence, the self-parent cycle brake on recursion, and exactly-one post-tree single-query invalidation (view-scoped deletes only; hook/RLS/parent-column/button variants skip it). Adapt to hosts without transaction-attached callbacks by ordering cache-write AFTER commit inside the same logical unit. Omit nothing portable. Coverage caveat: deterministic probes only at this pin.
