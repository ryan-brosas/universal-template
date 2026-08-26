<!-- capsule-v2 -->
# m2m junction heuristic — when does a plain table with two FKs become a many-to-many link, and how are both sides minted?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do you detect an associative/bridge table from shape alone and promote it into two mm link columns without duplicating existing ones?

## extractAndGenerateManyToManyRelations + isMMRelationExist
**Path/Symbol:** `packages/nocodb/src/services/meta-diffs.service.ts:isMMRelationExist` (:1323-1350), `extractAndGenerateManyToManyRelations` (:1352-1536).
**Signature:** `async extractAndGenerateManyToManyRelations(context, modelsArr: Array<Model>)` — runs as the FINAL step of syncBaseMeta over freshly synced models.
**Data Shape:** Junction predicate: exactly 2 belongs-to columns AND `<5 non-virtual columns` AND `primaryKeys.length === 2`. Each minted side carries the full six-id mm wiring (`fk_mm_model_id`, `fk_child_column_id`, `fk_parent_column_id`, `fk_mm_child_column_id`, `fk_mm_parent_column_id`).

### Decisive source
```ts
// check if table is a Bridge table(or Associative Table) by checking
// number of foreign keys and columns
// todo: impl better method to identify m2m relation
if (belongsToCols?.length === 2 && normalColumns.length < 5 && assocModel.primaryKeys.length === 2) {
```
```ts
const isRelationAvailInA = await this.isMMRelationExist(context, modelA, assocModel, belongsToCols[0]);
...
if (
  colOpt &&
  isMMOrMMLike(col) &&
  colOpt.fk_mm_model_id === assocModel.id &&
  colOpt.fk_child_column_id === colChildOpt.fk_parent_column_id &&
  colOpt.fk_mm_child_column_id === colChildOpt.fk_child_column_id
) { isExist = true; break; }
```
```ts
await Column.insert<LinksColumn>(context, {
  title: getUniqueColumnAliasName(modelA.columns, pluralize(modelB.title)),
  fk_model_id: modelA.id,
  fk_related_model_id: modelB.id,
  fk_mm_model_id: assocModel.id,
  fk_child_column_id: belongsToCols[0].colOptions.fk_parent_column_id,
  fk_parent_column_id: belongsToCols[1].colOptions.fk_parent_column_id,
  fk_mm_child_column_id: belongsToCols[0].colOptions.fk_child_column_id,
  fk_mm_parent_column_id: belongsToCols[1].colOptions.fk_child_column_id,
  type: RelationTypes.MANY_TO_MANY,
  // mm has a junction table (fk_mm_model_id set), so the version heuristic
  // resolves LinkToAnotherRecord to LTAR v2.
  uidt: UITypes.LinkToAnotherRecord,
  ...
});
await Model.markAsMmTable(context, assocModel.id, true);
```

**Flow:** per model: collect belongs-to columns → junction predicate → resolve both relatives → existence probe per side (same junction id + CROSS-WIRED column equality: candidate's fk_child_column_id must equal the bt column's fk_parent_column_id and vice versa through the mm fields) → missing sides get one Links-style LTAR insert each (title = pluralize(other table)) → markAsMmTable(true) → ALSO walk both related tables' HAS_MANY columns matching the same fk pair and `Column.markAsSystemField` (the hm twins of the junction FKs become system fields) → non-junction tables previously marked mm get markAsMmTable(false) demotion.
**Invariant:** The id cross-wiring is symmetric but NOT identity: A-side's `fk_child_column_id` = btCols[0]'s PARENT column while its `fk_mm_child_column_id` = btCols[0]'s CHILD column — flipping these silently breaks every mm read. Existence probing prevents duplicate minting on repeated syncs; the demotion branch (markAsMmTable false) keeps stale flags honest after schema edits.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `MetaDiffsService.isMMRelationExist` :1323-1350; grep confirms two `markAsMmTable` call sites (:1500 true, :1532 false) and two identical-shape Column.insert blocks (A :1423 / B :1465).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "extractAndGenerateManyToManyRelations markAsMmTable", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape heuristic + existence probe + symmetric id cross-wiring + system-field promotion of the hm twins. Adapt the `<5 normal columns` slack to your users' naming habits. Omit demotion only if your host never un-bridges tables.
