<!-- capsule-v2 -->
# Reference-graph CTE four-way OR closure — how do you fetch the transitive reference closure around a field set in ONE query?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the v1 calculation engine discover every field-level dependency edge reachable from a changed-field seed, treating the reference graph as undirected?

## getFieldGraphItems recursive CTE
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/reference.service.ts:getFieldGraphItems` (:184–236).
**Signature:** `getFieldGraphItems(startFieldIds: string[]): Promise<IGraphItem[]>` where `IGraphItem = { fromFieldId: string; toFieldId: string }`.
**Data Shape:** Reads meta-db tables `reference` (from_field_id/to_field_id rows). Returns deduped edge list; caller then runs in-process graph algorithms.

### Decisive source
```ts
this.on(
  _knex.raw(sql, [depsFromField, cdFromField, depsToField, cdToField]).wrap('(', ')')
);
this.orOn(
  _knex.raw(sql, [depsFromField, cdToField, depsToField, cdFromField]).wrap('(', ')')
);
this.orOn(
  _knex.raw(sql, [depsToField, cdFromField, depsFromField, cdToField]).wrap('(', ')')
);
this.orOn(
  _knex.raw(sql, [depsToField, cdToField, depsFromField, cdFromField]).wrap('(', ')')
);
```
(`sql = '?? = ?? AND ?? != ??'`; the CTE is `withRecursive('connected_reference', ['from_field_id','to_field_id'], nonRecursiveQuery.union(recursiveQuery))` followed by `distinct`.)

**Flow:** Seed edges touch startFieldIds on EITHER side (`whereIn from … orWhereIn to`) → each recursion step joins new edges to ANY already-connected endpoint pair under ALL FOUR orientation combinations (from=cd.from, from=cd.to, to=cd.from, to=cd.to) while excluding identity edges (`!=`) → DISTINCT collapse → result handed to in-process `filterDirectedGraph`.
**Invariant:** The four-way OR is what makes the directed `reference` table behave UNDIRECTED during closure; dropping any arm silently loses legal lookup/rollup chains whose edges were recorded in reverse orientation. Identity-edge exclusion (`deps != cd` per matching column pair) prevents self-loop infinite recursion.
**Probe:** `grep -cF 'this.orOn(' apps/nestjs-backend/src/features/calculation/reference.service.ts` → 3 (plus the leading `this.on(` = four orientations); `grep -cF "withRecursive('connected_reference'" <same>` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getFieldGraphItems connected_reference recursive", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the recursive-CTE-with-orientation-permutations pattern for any directed-edge table that must close transitively as undirected; adapt table/column names and the meta-vs-data db routing; omit teable's specific `filterDirectedGraph` post-filter if your consumer needs full closure rather than a seeded subgraph.
