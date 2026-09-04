<!-- capsule-v2 -->
# Form data assembly from metatables — how do you serve everything a form renderer needs without exposing raw schema?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you compile view-section metadata plus live reference-table values into one form payload, efficiently and safely?

## Promise-memoized table reads, field-option merge over col defaults, reference dropdowns blank-filtered, formula fields excluded
**Path/Symbol:** `app/server/lib/DocApi.ts:GET /forms/:vsId` handler (:1398–1536), default layout spec (:1439–1459), `_.memoize` table cache (:1461–1463), `getRefTableValues` (:1472–1487).
**Signature:** response `{formFieldsById, formLayoutSpec, formTableId, formTitle}`; internal `table(tableId) = _.memoize(() => readTable(...).then(r => asRecords(r, {includeId: true})))`.
**Data Shape:** metatables `_grist_Views_section` (layoutSpec JSON, parentKey=WidgetType.Form, tableRef), `_grist_Views_section_field` (parentId=sectionId, colRef, widgetOptions JSON), `_grist_Tables_column` (type, visibleCol, label, description, widgetOptions).

### Decisive source
```ts
// Cache the table reads based on tableId. We are caching only the PROMISE, not the result.
const table = _.memoize((tableId: string) =>
    readTable(req, activeDoc, tableId, {}, {}).then(r => asRecords(r, { includeId: true })));

const getRefTableValues = async (col) => {
    const refTableId = getReferencedTableId(col.type);
    let refColId;
    if (col.visibleCol) {
      const refCol = Tables_column.getRecord(col.visibleCol);
      if (!refCol) { return []; }
      refColId = refCol.colId;
    } else { refColId = "id"; }
    if (!refTableId || typeof refTableId !== "string" || !refColId) { return []; }
    const values = await getTableValues(refTableId, refColId);
    return values.filter(([_id, value]) => !isBlankValue(value));   // blanks never become choices
};

return [field.id, {
    colId,
    description: fieldOptions.description || col.description,
    question: options.question || col.label || colId,     // field widget opts beat column meta beats id
    options,                                              // {...colOptions, ...fieldOptions}
    type: extractTypeFromColType(col.type),
    refValues: isFullReferencingType(col.type) ? await getRefTableValues(col) : null,
}];
```
**Flow:** resolve section → verify it's a Form widget (404 FormNotFound otherwise) → pull section fields and DROP formula columns (unsupported in forms) → missing layoutSpec falls back to a generated Layout skeleton (2 labels + Section with up to INITIAL_FIELDS_COUNT Field leaves) → per-field: merge `{...colOptions, ...fieldOptions}`, derive question/description fallback ladders, and for referencing types fetch the target table ONCE (promise-cached across all fields pointing at it), choosing display column via visibleCol else raw id, blank values filtered out.
**Invariant:** memoizing the PROMISE (not awaited results) deduplicates concurrent reads while failing identically for all sharers of one failure — cache results instead and one error poisons every later field; skip memoization and N reference fields cause N full-table reads. Access through shares is gated upstream by the published-form check (`_assertIsPublishedForm`) — this handler assumes that ran.
**Probe:** `test/server/lib/docapi/DocApiForms.ts` (:294–330 published/unpublished/share variants; form-fields assertions earlier in suite).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "formFieldsById layoutSpec getRefTableValues INITIAL_FIELDS_COUNT WidgetType Form", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt promise-level caching + option-merge ladders for any "compile schema + data into render payload" endpoint. Adapt the layout skeleton to your renderer. Omit visibleCol resolution if you only ever show raw ids (you probably shouldn't).
