<!-- capsule-v2 -->
# single-query cache invalidator — after a table or column rename, which OTHER models' cached SQL is stale and how do you find them all?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** The compiled single-query (read/list) SQL bakes in physical names of joined models — what discovery algorithm finds every referrer, including transitive multi-hop Lookup/Rollup chains?

## single-query cache invalidator
**Path/Symbol:** `packages/nocodb/src/helpers/singleQueryCacheInvalidator.ts` — whole file 531L: `clearSingleQueryCacheForReferencingModels` (:60–109), `clearSingleQueryCacheForRenamedColumnReferences` (:126–184), `clearSingleQueryCacheForColumnReferences` (:195–245), `expandEmbeddingColumns` (:468–500).
**Signature:** three exported entry points `(context, modelId|oldCol, ncMeta?) → Promise<void>`; core closure walker `expandEmbeddingColumns(embeddingColumnIds, lookups, rollups, relationColsTargetingModel?) → void` (mutates set in place).
**Data Shape:** "embedding column" = column whose compiled SQL references another model's physical name; only relation/Lookup/Rollup columns embed (header comment :37–41 — formula references are explicitly NOT traversed).

### Decisive source
```ts
// :53–58 — the seed/expand contract (comment verbatim):
// Discovery is a reverse transitive closure over "embedding columns" — columns
// whose SQL references `modelId`:
//   seed   = relation columns whose target IS `modelId` (they JOIN it), then
//   expand = any Lookup/Rollup whose relation hops onto `modelId`, OR whose
//            looked-up / rolled-up target column is already an embedding column.
// Repeat until the set stops growing, then map the columns to their models.
// :474–487 — fixpoint loop:
let grew = true;
while (grew) {
  grew = false;
  for (const lk of lookups) {
    if (embeddingColumnIds.has(lk.fk_column_id)) continue;
    if (
      relationColsTargetingModel.has(lk.fk_relation_column_id) ||
      embeddingColumnIds.has(lk.fk_lookup_column_id)
    ) {
      embeddingColumnIds.add(lk.fk_column_id);
      grew = true;
    }
  }
  // ... same pattern for rollups with fk_rollup_column_id ...
}
```

**Flow:** TABLE-RENAME path: seed = link columns targeting the renamed model → expand to fixpoint over base-wide lookup/rollup rows → resolve column ids to owning models → delete the renamed model itself (caller clears it) → invalidate remaining models → then cross-base sweep. COLUMN-RENAME path adds: far-side models of relations whose FK IS the renamed column (`loadFarSideModelIdsForFkColumn` matches child/parent/mm_child/mm_parent slots :288–297), plus when `oldCol.pv` the Links pointing at its model (display-value surfaces in labels). NON-RENAME updates take the cheap one-hop variant (`loadDependentRelationColIds`) since no physical name changed ⇒ transitive referrers cannot be stale.
**Invariant:** (1) All three entries short-circuit `if (!Noco.isEE()) return;` BEFORE any metaList2 discovery query — CE must pay zero queries. (2) The renamed entity's OWN cache is never cleared here; callers own it. (3) The one-hop variant is correct ONLY for non-rename updates; using it for renames silently strands transitive referrers (the exact bug the fixpoint walk replaced per header :24–27). (4) `loadBaseLookupsAndRollups` loads sequentially, not Promise.all, "since ncMeta may be a single Knex transaction" (:350–353).
**Probe:** `grep -c "if (!Noco.isEE()) return;" packages/nocodb/src/helpers/singleQueryCacheInvalidator.ts` → `4`.
**Coverage caveat:** grep-derived; no unit spec covers this helper.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "clearSingleQueryCacheForReferencingModels expandEmbeddingColumns", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reverse transitive-closure algorithm and EE short-circuit placement; adapt MetaTable names; omit cross-base knex fallback nuances at your peril — see the cross-base capsule.
