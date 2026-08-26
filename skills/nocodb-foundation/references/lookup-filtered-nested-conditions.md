<!-- capsule-v2 -->
# lookup-over-filtered-lookup — where must each nested lookup level apply ITS OWN link conditions?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** A lookup over a filtered lookup silently ignores the inner filter — which relation sub-query must each level's conditions be applied to, and how is that table captured?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/db/generateLookupSelectQuery.ts` (capture decls :189/:476; assignments :240/:283/:329 first-level + :532/:583/:654 nested; application :400–:411 and :701–:712).
**Signature:** `extractLinkRelFiltersAndApply({ qb: selectQb, column, alias, table: <refBaseModel>.model, baseModel: <refBaseModel>, context })`.
**Data Shape:** `firstLevelRefBaseModel: IBaseModelSqlV2` / `nestedLevelRefBaseModel` — the RELATED (aliased) table whose columns this level's own conditions constrain; assigned per branch HM→parentBaseModel, BT/OO→childBaseModel, MM→junction parentBaseModel.

### Decisive source
```ts
// Apply the outer lookup's own link conditions ("limit record by filter")
// to the first-level relation sub-query. Without this, sort/group-by/rollup
// over a filtered lookup ignore its conditions. No-op for LTAR columns or
// when conditions are disabled (and a no-op stub in CE).
if (column.uidt === UITypes.Lookup && firstLevelRefBaseModel) {
  await extractLinkRelFiltersAndApply({ qb: selectQb, column, alias,
    table: firstLevelRefBaseModel.model, baseModel: firstLevelRefBaseModel, ... });
}
```

**Flow:** at EVERY relation-shape branch, capture the base model of the aliased related table BEFORE building its sub-query/join; after the level's select shape exists, apply that level's own link conditions onto `selectQb` — first level once (:400), then per intermediate NESTED Lookup level inside the loop (:701), never for plain LTAR hops (`nestedLookupColOpt` gate).
**Invariant:** (1) Conditions belong to the level that OWNS them — applying only at the outermost query drops inner filters entirely (#10150); applying to the wrong alias constrains the wrong table. (2) The capture must happen per-relation-type INSIDE each branch: the related table differs by shape (HM parent vs BT child vs MM junction). (3) Gating on `column.uidt === Lookup` / `nestedLookupColOpt` keeps LTAR display resolution untouched. (4) Mirrors an existing EE display path — CE stub makes it a no-op there.
**Probe:** `grep -c "extractLinkRelFiltersAndApply" packages/nocodb/src/db/generateLookupSelectQuery.ts` → 3 (import + 2 sites); `sed -n '395,411p'` shows the first-level block verbatim. No upstream unit suite (runner caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "generateLookupSelectQuery extractLinkRelFiltersAndApply nested lookup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-level condition ownership + per-shape capture; adapt naming; omit CE stub handling if your host has no CE split.
