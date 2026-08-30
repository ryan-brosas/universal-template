<!-- capsule-v2 -->
# DocAction notification categories — how do you summarize a pile of raw doc actions into human notification categories without leaking noise?

**Source:** grist-core (Apache-2.0), `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How should internal-table changes map to user-meaningful change categories, and which tables must stay invisible?

## describeDocActions category map
**Path/Symbol:** `app/server/lib/describeDocActions.ts:describeDocActions` (135-151), `allCategories` (112-121), `categoryMap` (163-188), `sortDocActionCategories` (156-158).
**Signature:** `describeDocActions(docActions: DocAction[], docData: DocData): DocActionsDescription | null` where `DocActionsDescription = { userTableNames: string[], categories: DocActionCategory[] }`; `sortDocActionCategories(categories: Set<DocActionCategory>): DocActionCategory[]`.
**Data Shape:** Fixed ordered category vocabulary: `metadata, settings, structure, layouts, forms, webhooks, access rules, user attributes` — the array doubles as the canonical sort order. Map values are THREE-valued: category string | `IGNORE` sentinel (Symbol) | `null` (deprecated).

### Decisive source
```ts
for (const action of docActions) {
  const tableId = getTableId(action);
  if (!isMetadataTable(tableId)) {
    userTableNameSet.add(getTableName(tableId, docData) || tableId); // friendly title or raw id
  } else {
    const category = categoryMap[tableId as keyof SchemaTypes] || "metadata";
    if (category === IGNORE) { continue; }
    categorySet.add(category);
  }
}
if (userTableNameSet.size === 0 && categorySet.size === 0) { return null; }
// _grist_Cells: IGNORE      — comments have their own notification config
// _grist_Attachments: IGNORE — accompanied by a user-table change or cleanup only
// _grist_Imports/_grist_TabItems/... : null — deprecated, silently dropped
```

**Flow:** Split actions by `isMetadataTable`: user tables accumulate display names resolved via `tableRec.rawViewSectionRef → _grist_Views_section.title` (fallback raw tableId); metadata tables map through the category table — unknown tables fall to `"metadata"` (catch-all), `IGNORE` drops entirely, `null` marks deprecated tables that also drop. Empty overall ⇒ `null` (nothing to notify). Sorting filters the fixed `allCategories` array by set membership so output order is stable regardless of insertion order.
**Invariant:** Comments (`_grist_Cells`) must NEVER appear in doc-change notifications — they carry a dedicated notification configuration, and double-reporting breaks product behavior (in-source comment 131-134). The three-valued map is load-bearing: collapsing `null`/`IGNORE`/unknown into one bucket would resurrect deprecated-table noise or swallow genuinely new metadata tables.
**Probe:** No dedicated unit test (coverage caveat). Deterministic anchors: `grep -n "IGNORE\|allCategories" app/server/lib/describeDocActions.ts` → sentinel at :161, vocabulary at :112; consumption at trigger-notification call sites.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "describeDocActions DocActionCategory", limit: 5 });
```
## Verdict
Adopt the ordered vocabulary + three-valued table map (category/ignore/deprecated) + friendly-name-with-raw-fallback for any change-feed summarizer; adapt category words to your domain; omit Grist's specific deprecated-table list.
