<!-- capsule-v2 -->
# Nested lookup join walker — how do you flatten an N-level Lookup chain (lookup-of-lookup-of…) into one JOIN spine?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does the builder walk a nested lookup chain and where do per-level limits, soft-delete filters, and link filters attach at each depth?

## while-loop chain flattening
**Path/Symbol:** `packages/nocodb/src/db/formulav2/lookup-or-ltar-builder.ts` while-loop (:313-525).
**Signature:** loop invariant: `selectQb` is a QueryBuilder accumulating joins; `prevAlias` = alias of the PREVIOUS level's table; `lookupContext` = refContext of the previous level; terminal value = first non-Lookup `lookupColumn`.
**Data Shape:** Each iteration mints ONE `__nc_formula<N>` nestedAlias plus one extra `__nc<M>` assocAlias for MM levels; aliases come from the shared monotonic counter.

### Decisive source
```ts
// :371-380 — nested link filters attach to THIS level's alias, not level one's:
await extractLinkRelFiltersAndApply({
  context, column: lookupColumn, table: parentModel,
  baseModel: parentBaseModel, qb: selectQb,
  // this nested level's related table is joined as `nestedAlias`,
  // not the first-level `alias` — see the mm-lookup filter fix.
  alias: nestedAlias,
});
// :361-369 — BT nesting joins prevAlias.fk → nestedAlias.pk:
selectQb.join(
  dbQueryClient.tableAlias(knex, parentBaseModel.getTnPath(parentModel.table_name), nestedAlias),
  `${prevAlias}.${childColumn.column_name}`,
  `${nestedAlias}.${parentColumn.column_name}`,
);
// :523-524 — advance BOTH cursors or the next iteration re-joins level N:
lookupColumn = await nestedLookup.getLookupColumn(refContext);
prevAlias = nestedAlias;
```

**Flow:** while current lookupColumn is a Lookup → resolve its relation → fork BT/HM/MM adding INNER joins chained off prevAlias → apply this level's link filters + aliased soft-delete filter → (PG only) apply `applyNestedLookupLevelLimit` for BT/HM when THIS level's column carries a limit config → advance lookupColumn/prevAlias/lookupContext.
**Invariant:** (1) MM nesting joins junction FIRST on the child side (`assoc.mmChild = prev.child`, :483-484) then parent side — reversing the join order silently cross-products. (2) Soft-delete filtering happens at EVERY level with that level's base model + alias — skipping one level resurrects deleted rows mid-chain. (3) The loop deliberately has NO recursion-depth cap: chains longer than SQL's join budget die in the engine, not here. (4) Per-level limits are PG-only and read config from the CURRENT level's lookupColumn (`loadLookupSortAndLimit(context, lookupColumn)`), not from the root column.
**Probe:** No unit tests upstream. Deterministic probe: grep :378 comment "see the mm-lookup filter fix" — the wrong-alias regression it documents; search_graph resolves `applyNestedLookupLevelLimit` under `db/lookupSortLimit`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "nestedConditionJoin", limit: 10 });
// twin implementation for the FILTER plane lives in field-handler/utils/handlerUtils.ts
```

## Verdict
Adopt the cursor-pair loop shape (value cursor + alias cursor) and per-level filter attachment; adapt alias minting to your builder; omit the commented-out dead join block (:517-521). Caveat: no direct tests at pin.
