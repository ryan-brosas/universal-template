<!-- capsule-v2 -->
# Hook filter tree flatten — why did creation-order child attachment break, and what replaces it?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When filters support reordering, how do you rebuild a parent/child filter hierarchy from a flat list so import/duplicate flows see the right sequence?

## HookFilter.Filter.getFilterObject
**Path/Symbol:** `packages/nocodb/src/models/HookFilter.ts:getFilterObject` (:309-407); recursive delete (:207-227); multi-scope cache registration `redisPostInsert` (:106-173).
**Signature:** `static async getFilterObject(context, { viewId }, ncMeta): Promise<FilterType>` — returns ONE synthetic root `{is_group: true, children: [], logical_op: 'and'}` whose children are the FLATTENED tree in deterministic order.
**Data Shape:** Flat FILTER_EXP rows carry `{id, fk_parent_id, order, is_group, logical_op, comparison_op, value, fk_column_id, fk_view_id}`. A twin implementation lives at `Filter.ts:669-830` (view filters); this one serves HOOK views.

### Decisive source
```ts
/**
 * NOTE:
 * Earlier implementation relied on filter creation order when attaching children.
 * Now that filters support reordering, creation order is no longer reliable.
 *
 * This caused flattened filters to appear in the wrong sequence, leading to
 * incorrect parent–child relationships during import / duplicate base flows.
 *
 * The new approach explicitly groups by `fk_parent_id`, sorts by `order`,
 * and flattens the tree deterministically to preserve correct hierarchy.
 */
// parentId -> children
const childrenMap = new Map<string, FilterType[]>();
for (const filter of filters) {
  const parentId = filter.fk_parent_id ?? 'root';
  (childrenMap.get(parentId) ?? childrenMap.set(parentId, []).get(parentId)!).push(filter);
}
for (const [, list] of childrenMap) list.sort((a, b) => (a.order ?? Infinity) - (b.order ?? Infinity));
const flat: FilterType[] = [];
const walk = (parentId: string) => {
  const children = childrenMap.get(parentId);
  if (!children) return;
  for (const child of children) { flat.push(child); walk(child.id!); }  // parent FIRST, then children
};
walk('root');
result.children = flat;
```

**Flow:** cached list read under `[FILTER_VIEW, viewId]` scope ordered by `order` → DB fallback metaList2 → group by fk_parent_id ('root' for null) → sibling sort with `?? Infinity` (unordered last, stable) → DFS from root pushing PARENT before its children → assign flat array. Insert path registers each new row's cache key under up to FOUR lists (view, view+parent, parent, column scopes); delete recurses children-first then deepDel CHILD_TO_PARENT.
**Invariant:** The flatten must be parent-first DFS — consumers treat position as evaluation order for grouped conditions. Sorting must tolerate missing `order` (Infinity) or legacy rows vanish from their sibling group. Creation order is explicitly NOT trusted anymore; any port that re-derives hierarchy from row ordering reintroduces the documented bug.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves BOTH twins (`HookFilter.Filter.getFilterObject` :309-407 AND `Filter.Filter.getFilterObject` :669-830); grep confirms one childrenMap build per twin and the 'root' sentinel.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getFilterObject childrenMap fk_parent_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt group-by-parent + order-sort + parent-first DFS flatten for ANY hierarchical metadata consumed positionally. Adapt the 'root' sentinel to your null-parent convention. Omit the four-scope cache registration if your cache has no list-append discipline (but then audit your invalidation).
