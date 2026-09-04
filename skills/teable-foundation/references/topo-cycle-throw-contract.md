<!-- capsule-v2 -->
# Topo-order cycle contract — how does field-graph topo sorting report cycles, and why do start nodes get PREPENDED not merged?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What exact ordering/cycle semantics must a porter reproduce when recomputing the v1 dependency order?

## getTopoOrders + prependStartFieldIds
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/utils/dfs.ts:getTopoOrders` (:64–138), `:prependStartFieldIds` (:56–61), `:hasCycle` (:15–54).
**Signature:** `getTopoOrders(graph: IGraphItem[]): ITopoItem[]`; `prependStartFieldIds(topoOrders: ITopoItem[], startFieldIds: string[]): ITopoItem[]`.
**Data Shape:** `ITopoItem = { id: string; dependencies: string[] }` — dependencies are INCOMING edges (reverse adjacency). Output is dependency-first order.

### Decisive source
```ts
if (visitingNodes.has(node)) {
  throw new CustomHttpException(
    `Detected a cycle: ${node} is part of a circular dependency`,
    HttpErrorCode.VALIDATION_ERROR,
    { localization: { i18nKey: 'httpErrors.field.cycleDetected' } }
  );
}
...
// Start with nodes that have no outgoing edges (leaf nodes)
const startNodes = Array.from(allNodes).filter(
  (node) => !adjList[node] || adjList[node].length === 0
);
```
```ts
export function prependStartFieldIds(topoOrders: ITopoItem[], startFieldIds: string[]) {
  const existFieldIds = new Set(topoOrders.map((item) => item.id));
  const newTopoOrders = startFieldIds
    .filter((fieldId) => !existFieldIds.has(fieldId))
    .map((fieldId) => ({ id: fieldId, dependencies: [] }));
  return [...newTopoOrders, ...topoOrders];
}
```

**Flow:** DFS from leaf nodes (no outgoing edges) visiting dependencies first → push node AFTER its dependencies (post-order = dependency-first list) → any re-entry into an on-stack node throws the localized VALIDATION_ERROR instead of returning a partial order. Separately, changed-field seeds that are NOT in the graph (e.g. plain fields with no dependents) are synthesized as `{id, dependencies: []}` and prepended so consumers can still address them.
**Invariant:** Cycle detection is a THROW at plan time, never a silent truncation — a porter who "recovers" from cycles changes product behavior (teable surfaces formula cycles to users as validation errors). Prepend dedupes against existing ids; it never duplicates or reorders discovered nodes.
**Probe:** `grep -cF 'cycleDetected' apps/nestjs-backend/src/features/calculation/utils/dfs.ts` → 1; direct test `apps/nestjs-backend/src/features/calculation/utils/dfs.spec.ts` pins DAG orders, self-loop→true, empty→false, pruneGraph cases (7 pruneGraph assertions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getTopoOrders cycle detection topological", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt throw-on-cycle + post-order dependency-first emission + prepend-missing-seeds as a triple; adapt error type/localization to host; omit `topoOrderWithStart`/`pruneGraph` unless your consumer needs single-root suborders.
