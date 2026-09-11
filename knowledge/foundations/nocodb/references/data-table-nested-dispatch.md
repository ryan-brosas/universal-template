<!-- capsule-v2 -->
# Nested-link relation dispatch — which baseModel method serves each LTAR relation type, and what must be sanitized before the query compiles?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When porting the `/row/:rowId/:columnId` nested endpoints, how does one method route bt/oo/mo vs hm vs mm/mm-like relations, and where exactly do caller predicates get stripped?

## DataTableService.nestedDataList + getColumn
**Path/Symbol:** `packages/nocodb/src/services/data-table.service.ts:nestedDataList` (:486-638), `getColumn` (:640-654), `nestedLink` (:657-699), `nestedReorder` (:705-739), `nestedUnlink` (:742-780).
**Signature:** `async nestedDataList(context: NcContext, param: { viewId; modelId; query; rowId; columnId; apiVersion? })`.
**Data Shape:** Dispatch keys are the SDK type guards over the Column: `isBtLikeV2Junction(column)` (v2 MO/OO — junction with LIMIT 1), `isMMOrMMLike(column)` (v2 OM/MM + v1 mm), `colOptions.type === RelationTypes.HAS_MANY`, else BELONGS_TO/`meta?.bt` → single-object reads.

### Decisive source
```ts
// The related table may live in another base (cross-base link). Build the
// projection in the related table's own context — otherwise `getAst` loads its
// columns under the parent base, resolves none, and `nocoExecute` below strips
// every field (returning empty `{}` records). Mirrors `getLinkedDataList`.
const { refContext } = colOptions.getRelContext(context);
const relatedModel = await colOptions.getRelatedTable(refContext);

// Strip caller-supplied where/sort references to columns the link doesn't expose
// (cross-base / visibility-limited related tables). This is NOT the view-`show`
// dimension (view-hidden columns stay queryable) — it's the cross-base isolation
// / table-visibility ACL boundary. Both the data fetch and the count read from
// `param.query`, so sanitizing it here covers both surfaces.
await restrictNestedLinkQuery(context, colOptions, relatedModel, param.query);

const { ast, dependencyFields } = await getAst(refContext, {
  model: relatedModel,
  query: param.query,
  extractOnlyPrimaries: !(param.query?.f || param.query?.fields),
  fk_display_value_column_id: (colOptions as any).fk_display_value_column_id,
});
```
then:
```ts
if (isBtLikeV2Junction(column)) {
  data = await baseModel.mmRead({ colId: column.id, parentId: param.rowId }, listArgs as any);
} else if (isMMOrMMLike(column)) {           // array via junction
  data = await baseModel.mmList({ colId: column.id, parentId: param.rowId, apiVersion }, listArgs);
  count = await baseModel.mmListCount({ colId: column.id, parentId: param.rowId }, param.query);
} else if (colOptions.type === RelationTypes.HAS_MANY) {
  data = await baseModel.hmList({ colId: column.id, id: param.rowId, apiVersion }, listArgs);
  count = await baseModel.hmListCount({ colId: column.id, id: param.rowId }, param.query);
} else if (colOptions.type !== RelationTypes.BELONGS_TO && !column.meta?.bt) {
  data = await baseModel.ooRead({ colId: column.id, id: param.rowId, apiVersion }, param.query);
} else {
  data = await baseModel.btRead({ colId: column.id, id: param.rowId, apiVersion }, param.query);
}
```

**Flow:** getModelAndView → exist(rowId) gate → getColumn (must be LTAR **and** belong to model) → colOptions.getRelContext → related model in refContext → restrictNestedLinkQuery MUTATES param.query in place (data fetch AND count read it) → getAst over refContext (extractOnlyPrimaries unless explicit f/fields) → five-way dispatch → nocoExecute → BELONGS_TO returns bare data; everything else wraps PagedResponseImpl with the separately-counted total.
**Invariant:** (1) The related model is ALWAYS resolved under refContext from `getRelContext`, never the caller's context — cross-base links resolve zero columns otherwise and nocoExecute strips every field to empty objects. (2) Sanitization happens before getAst because both the list and the count compile from `param.query`. (3) The strip targets the CROSS-BASE/VISIBILITY boundary, not the view-show dimension — hidden-by-view columns stay queryable here. Link add/remove/unlink validate ids first (`validateIds`: null → recordNotFound, repeated id → duplicateRecord) and reorder passes `before ?? null`.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `DataTableService.nestedLink` :657-699 and controller twin `DataTableController.nestedLink` :226-252; grep confirms `restrictNestedLinkQuery(` appears once in this file (:530).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "nestedDataList mmList hmList btRead ooRead", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-way guard ladder keyed on SDK type predicates, the refContext resolution for cross-base links, and mutate-in-place query confinement before any compile. Adapt method names (mmRead/mmList/hmList/btRead/ooRead) to your storage layer's vocabulary. Omit the v1/v2 duality only if your host never mixes link versions.
