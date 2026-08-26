<!-- capsule-v2 -->
# rename-gated invalidation dispatch — when must the expensive transitive walk run instead of the one-hop scan?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Model.update and Column.update each hold two invalidator flavors — what exact condition selects the transitive graph walk, and why is the cheap scan safe otherwise?

## rename-gated invalidation dispatch
**Path/Symbol:** `packages/nocodb/src/models/Model.ts` :1050–1056; `packages/nocodb/src/models/Column.ts` :1705–1718 and delete-path :1970.
**Signature:** table: `if (oldModel.table_name !== table_name) await clearSingleQueryCacheForReferencingModels(...)` — column: `if (oldCol.column_name !== updatedColumn.column_name) clearSingleQueryCacheForRenamedColumnReferences(...) else clearSingleQueryCacheForColumnReferences(...)`.
**Data Shape:** callers always run `View.clearSingleQueryCache(context, id, null, ncMeta)` for the CHANGED entity first (:1049); the referrer sweep is strictly additional.

### Decisive source
```ts
// Model.ts :1052–1056 (comment verbatim):
// A physical table rename invalidates the compiled single-query SQL of every
// model that embeds this table's name — directly via a Link/LTAR, OR via a
// transitive Lookup/Rollup chain. Only walk that graph when the physical
// name actually changed; a title-only rename leaves the SQL untouched.
if (oldModel.table_name !== table_name) {
  await clearSingleQueryCacheForReferencingModels(context, tableId, ncMeta);
}
// Column.ts :1709–1718:
if (oldCol.column_name !== updatedColumn.column_name) {
  await clearSingleQueryCacheForRenamedColumnReferences(context, oldCol, ncMeta);
} else {
  await clearSingleQueryCacheForColumnReferences(context, oldCol, ncMeta);
}
```

**Flow:** compare OLD vs NEW PHYSICAL names (table_name / column_name), not titles → physical change ⇒ full dependency-graph walk (renames bake into compiled SQL of referrers); title-only or non-rename update ⇒ cheap one-hop relation/lookup/rollup scan ⇒ column DELETION always takes the cheap path with the old col object (:1970).
**Invariant:** The gate compares physical names only. A title rename changes display surfaces but NOT compiled SQL — running the transitive walk there wastes base-wide meta scans for zero stale caches. Conversely, gating the cheap path on "no rename" is sound because lookup/rollup metadata references COLUMN IDS; only a physical rename changes the string baked into already-compiled queries.
**Probe:** `grep -c "clearSingleQueryCacheFor" packages/nocodb/src/models/Model.ts packages/nocodb/src/models/Column.ts | wc -l` → files matched: `2` (one call site in Model.ts:1055; two in Column.ts:1711/:1717 plus delete at :1970).
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "clearSingleQueryCacheForReferencingModels tableUpdate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the physical-name-equality gate as the dispatch contract between the two invalidators; adapt naming; omit nothing — misrouting the gate reintroduces either stale SQL (cheap-on-rename) or wasted scans (walk-on-title).
