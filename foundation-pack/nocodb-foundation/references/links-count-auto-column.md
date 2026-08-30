<!-- capsule-v2 -->
# links-count auto column — what does checking "Links" on a relation create, and why is the grid column force-hidden?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** populateRollupForLTAR synthesizes a count column when a link field is created — what are its exact coordinates and view side effects?

## links-count auto column
**Path/Symbol:** `packages/nocodb/src/helpers/columnHelpers.ts` — `populateRollupForLTAR` (:626–671).
**Signature:** `populateRollupForLTAR({context, column, columnMeta?, alias?}) → Promise<void>` where `column` is the freshly created LTAR/Links relation column.
**Data Shape:** inserted column: `uidt: UITypes.Links` (the count-flavored twin), `rollup_function: 'count'`, `fk_rollup_column_id: relatedModel.primaryKey?.id || first-column id`, `fk_relation_column_id: column.id`, meta plural/singular of RELATED model title.

### Decisive source
```ts
// :645–670:
const pkId =
  relatedModel.primaryKey?.id ||
  (await relatedModel.getColumns(context))[0]?.id;
...
await Column.insert<RollupColumn>(context, {
  uidt: UITypes.Links,
  title: getUniqueColumnAliasName(
    await model.getColumns(context),
    alias || `${relatedModel.title} Count`,
  ),
  fk_rollup_column_id: pkId,
  fk_model_id: model.id,
  rollup_function: 'count',
  fk_relation_column_id: column.id,
  meta,
});

const viewCol = await GridViewColumn.list(context, views[0].id).then((cols) =>
  cols.find((c) => c.fk_column_id === column.id),
);
await GridViewColumn.update(context, viewCol.id, { show: false });
```

**Flow:** load owning model's views → resolve related model via the relation's colOptions → pick pk fallback (primaryKey or FIRST column) → insert the Links-count column titled `<Related> Count` (alias wins; uniqueness resolved against existing titles) → find the RELATION column's grid-view entry in views[0] and set show:false.
**Invariant:** The hidden column is the RELATION's own grid entry (`fk_column_id === column.id`), NOT the new count column — the count column appears, the raw link selector disappears from the default grid. `views[0]` is assumed to exist and be a grid; pkId falls back to first column so tables without a declared pk still aggregate. Title pattern `<RelatedTitle> Count` is API-visible contract (tests/UI match it).
**Probe:** `grep -c "rollup_function: 'count'" packages/nocodb/src/helpers/columnHelpers.ts` → `1`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "populateRollupForLTAR Links Count", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt uidt-Links + count + pk-fallback + hide-relation-grid-entry as one atomic behavior; adapt title template if UI strings diverge.
