<!-- capsule-v2 -->
# Filter-tree flatten twin — why do two classes carry byte-similar getFilterObject trees, and where do they drift?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** Filter (view/hook/link/widget/RLS/button filters) and HookFilter both own `getFilterObject` — which parts are copy-invariants and which parts legitimately differ?

## Filter.getFilterObject vs HookFilter.getFilterObject
**Path/Symbol:** `packages/nocodb/src/models/Filter.ts:getFilterObject` (:669-830); `packages/nocodb/src/models/HookFilter.ts:getFilterObject` (:309-407). Both internally `new Filter(...)`/class named Filter (HookFilter extends Filter per pass-8 hook-filter-tree-flatten capsule).
**Signature:** Filter takes `{ viewId?, hookId?, linkColId?, parentColId?, widgetId?, rlsPolicyId?, buttonColId? }` (7 scopes); HookFilter takes `{ viewId }` only.
**Data Shape:** Returns synthetic root `{ is_group: true, children: [], logical_op: 'and' }` with a FLAT, parent-first DFS-ordered children array.

### Decisive source
```ts
// IDENTICAL in both twins — the reorder-fix NOTE (quoted from HookFilter :350-360):
// Earlier implementation relied on filter creation order when attaching children.
// Now that filters support reordering, creation order is no longer reliable.
// This caused flattened filters to appear in the wrong sequence, leading to
// incorrect parent–child relationships during import / duplicate base flows.
// The new approach explicitly groups by `fk_parent_id`, sorts by `order`,
// and flattens the tree deterministically to preserve correct hierarchy.

// 1️⃣ group:  const parentId = filter.fk_parent_id ?? 'root';
// 2️⃣ sort:   list.sort((a, b) => (a.order ?? Infinity) - (b.order ?? Infinity));
// 3️⃣ DFS:    flat.push(child); walk(child.id!);   // parent BEFORE children
// 4️⃣ result.children = flat;
```
```ts
// DRIFT 1 — cache key shape:
// HookFilter (:318-323): explicit two-part scope tuple
await NocoCache.getList(context, CacheScope.FILTER_EXP,
  [FilterCacheScope.VIEW, viewId], { key: 'order' });
// Filter (:690-705): bare-id fallback chain
await NocoCache.getList(context, CacheScope.FILTER_EXP,
  [parentColId || viewId || hookId || linkColId || widgetId || rlsPolicyId || buttonColId],
  { key: 'order' });
```
```ts
// DRIFT 2 — precedence ladders DISAGREE between the condition build and the
// cache-scope stamp inside Filter itself:
// condition (:711-725): viewId && !parentColId → hookId → linkColId → parentColId → widgetId → rlsPolicyId → buttonColId
// cacheScope (:741-755): parentColId → viewId → hookId → linkColId → widgetId → rlsPolicyId → buttonColId
```
```ts
// DRIFT 3 — DB ordering: Filter adds `orderBy: { order: 'asc' }` to metaList2 (:733-735);
// HookFilter's metaList2 has NO orderBy (:327-334) — it relies on the in-memory sort alone.
```

**Flow:** cache-list probe keyed on scope id → on miss, DB metaList2 over FILTER_EXP with the scope condition → setList under the scope tag → group-by-parent → sort siblings (`order ?? Infinity`) → deterministic parent-first DFS flatten into one flat array under a synthetic and-root. Downstream consumers walk the flat array rebuilding nesting via fk_parent_id.
**Invariant:** When you fix tree-ordering logic, fix it in BOTH twins — upstream's reorder bug shipped because creation order was trusted; the NOTE documents the incident class ("incorrect parent–child relationships during import / duplicate base flows"). The precedence mismatch between Filter's condition ladder and its own cacheScope ladder is a live latent trap: a caller passing BOTH parentColId and viewId queries the DB by parent-column but caches under VIEW — cross-scope pollution on shared ids. Porters copying one ladder but not the other inherit the inconsistency.
**Probe:** Runner blocked at this pin. Deterministic probe (graph adversarial already confirmed both twins): grep shows the identical NOTE block at Filter :781-790 and HookFilter :350-360; `orderBy` appears once in each file's getFilterObject region (Filter yes :733, HookFilter no).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getFilterObject fk_parent_id childrenMap", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deterministic group→sort→DFS-flatten contract for ANY stored tree flattened into ordered lists. Adapt scope keys to your entity types. Omit nothing else — and if you port only ONE twin, port Filter's (superset), but keep its cache-scope/condition ladders consistent, unlike upstream's current divergence.
