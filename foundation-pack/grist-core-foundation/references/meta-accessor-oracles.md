<!-- capsule-v2 -->
# Metadata accessor oracles — should lookups of document metadata fail soft or loud?

**Source:** grist-core (Apache-2.0), `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What contract do server-side helpers follow when reading `_grist_Tables` / `_grist_Views_section` records by id?

## ActiveDocUtils accessors
**Path/Symbol:** `app/server/lib/ActiveDocUtils.ts:getRecordById` (44-55), `getDocDataOrThrow` (35-42), family wrappers (7-33).
**Signature:** `function getRecordById<TableId extends keyof SchemaTypes>(doc: ActiveDoc, tableId: TableId, id: number)` (module-private); exports `getTableById`, `getTableColumnById`, `getTableColumnsByTableId(tableId: number)`, `getWidgetById`, `getWidgetsByPageId(pageId: number)`, `getDocDataOrThrow(doc)`.
**Data Shape:** Reads in-memory `DocData` meta tables (`_grist_Tables`, `_grist_Tables_column`, `_grist_Views`, `_grist_Views_section`). Returns raw meta records (`MetaRowRecord`); child lookups filter by `parentId`.

### Decisive source
```ts
export function getDocDataOrThrow(doc: ActiveDoc) {
  const docData = doc.docData;
  if (!docData) { throw new Error("Document not ready"); }
  return docData;
}
function getRecordById<TableId extends keyof SchemaTypes>(doc, tableId, id) {
  const record = getDocDataOrThrow(doc).getMetaTable(tableId).getRecord(id);
  if (!record) { throw new Error(`${getRecordName(tableId)} ${id} not found`); }
  return record;
}
// getRecordName: _grist_Tables->"Table", _grist_Tables_column->"Column",
//                _grist_Views_section->"Widget", default->"Record"
```

**Flow:** Every accessor enters through `getDocDataOrThrow` (document-loaded gate), then either `getRecord(id)` (loud oracle) or `filterRecords({parentId})` (list). Consumers like `selectBy.getSelectByOptions` build widget-link option matrices directly on these throws-as-validation-errors. Child listings compose: page → `_grist_Views` record → sections filtered by `parentId`.
**Invariant:** Missing metadata is an ERROR with a human-friendly subject name ("Widget 42 not found"), never `undefined` — callers depend on loud failure to produce user-facing validation messages. Document-not-ready is checked at EVERY entry point, not cached, because `docData` flips during load/shutdown.
**Probe:** No dedicated unit suite (coverage caveat). Exercised indirectly through `test/nbrowser/SelectBySummaryRef.ts` and server suites importing these helpers. Deterministic anchor: `grep -n "not found" app/server/lib/ActiveDocUtils.ts` → 1 hit at :51; `grep -n "Document not ready" ...` → 1 hit at :38.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "ActiveDocUtils getWidgetById getTableById", limit: 5 });
```
## Verdict
Adopt loud, subject-named lookup failures plus an explicit ready-gate for any metadata facade over a loading/closing document; adapt table ids/error wording; omit SchemaTypes keying if your host lacks a schema-typed table union.
