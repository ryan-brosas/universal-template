<!-- capsule-v2 -->
# Widget link compatibility matrix — how do you enumerate every valid source→target cursor-link pair between widgets on one page?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you compute the full set of "Select By" options (which widget can feed which) from page metadata alone?

## Cross-product of per-page LinkNodes filtered through a pure `isValidLink` predicate, summary tables projected to their source
**Path/Symbol:** `app/server/lib/selectBy.ts:getSelectByOptions` (:26–49); node builders `createNodes` (:51–61), `getLinkNodeTableById` (:63–78), `getLinkNodeSection` (:80–106); predicates live in `app/common/LinkNode.ts` (`isValidLink`, `buildLinkNodes`).
**Signature:** `function getSelectByOptions(doc: ActiveDoc, widgetId: number): SelectByOption[]`; `interface SelectByOption { link_from_widget_id: number; link_from_column_id: string | null; link_to_column_id: string | null }`.
**Data Shape:** reads `_grist_Views_section` (widgets), `_grist_Tables`/columns via ActiveDocUtils getters; emits LinkNodes `{ section, table, column? }` where summary-table widgets report the SOURCE table's id plus `isSummaryTable`.

### Decisive source
```ts
const targetWidget = getWidgetById(doc, widgetId);
const sourceWidgets = getWidgetsByPageId(doc, targetWidget.parentId);
const targetNodes = createNodes(doc, [targetWidget]);
const sourceNodes = createNodes(doc, sourceWidgets);
const options: SelectByOption[] = [];
for (const sourceNode of sourceNodes) {
  const validTargetNodes = targetNodes.filter(targetNode => isValidLink(sourceNode, targetNode));
  for (const targetNode of validTargetNodes) {
    options.push({
      link_from_widget_id: sourceNode.section.id,
      link_from_column_id: sourceNode.column?.colId ?? null,
      link_to_column_id: targetNode.column?.colId ?? null,
    });
  }
}
```

**Flow:** resolve the target widget → gather ALL sibling widgets on the SAME page (parentId) → lift each side into LinkNodes: sections carry their widget's link fields, tables resolve summary tables to their underlying source tableId so a summary can link like its base table → take the cross product sources×targets and keep pairs passing the shared `isValidLink` predicate (cursor-link type rules: same table family, compatible column directions) → emit one option per surviving pair with null column ids when the link doesn't bind columns.
**Invariant:** Options are scoped to ONE page — cross-page linking is not considered here. The summary-table substitution happens at NODE-BUILD time (both builders do `maybeSummaryTable?.tableId ?? table.tableId`), so the validity predicate never sees synthetic table ids; porters who skip it wrongly exclude summary-widget links or match on the summary's own name. Column ids are nullable by design — validity and binding are separate concerns.
**Probe:** `test/nbrowser/SelectBySummaryRef.ts` (behavioral coverage for the summary-ref case; no server unit test — caveat). Deterministic source probes: `grep -n "isValidLink(sourceNode" app/server/lib/selectBy.ts` hits :37 exactly once; both `maybeSummaryTable?.tableId ?? table.tableId` occurrences at :70/:104.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "getSelectByOptions isValidLink LinkNode SelectByOption", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape "build normalized nodes (project derived entities to base), then filter a cross product with one pure predicate" for any compat-matrix UI (link options, join suggestions, integration targets). Adapt the node fields and predicate to your link taxonomy. Omit the summary projection if your domain has no derived-view entity.
