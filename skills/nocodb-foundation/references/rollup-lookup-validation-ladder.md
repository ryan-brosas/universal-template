<!-- capsule-v2 -->
# rollup/lookup payload validation — which errors must fire before any column is created, and how is a circular lookup chain detected?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the ordered validation ladder for rollup and lookup creation requests, and why does the mm case override relation.type?

## rollup/lookup payload validation
**Path/Symbol:** `packages/nocodb/src/helpers/columnHelpers.ts` — `validateRollupPayload` (:401–501), `validateLookupPayload` (:503–586).
**Signature:** `validateRollupPayload(context, payload: ColumnReqType | Column)`; `validateLookupPayload(context, payload, columnId?)`.
**Data Shape:** required params via validateParams (`title`, `fk_relation_column_id`, `fk_rollup_column_id`/`fk_lookup_column_id`, `rollup_function` for rollup); resolution fork: `const relationType = isMMOrMMLike(column) ? 'mm' : relation.type`.

### Decisive source
```ts
// :470–488 — the physical-existence rationale (comment verbatim):
// Rolling up a link/lookup/barcode-style column would build SQL against a
// column that doesn't physically exist, breaking every read of the table.
if (!isRollupAggregatableColumn(rollupColumn)) {
  const aggregatable = relatedTableColumns
    .filter((c) => !c.system && isRollupAggregatableColumn(c) &&
      getAvailableRollupForUiType(c.uidt).length)
    .map((c) => c.title);
  NcError.get(context).badRequest(
    `Field "${rollupColumn.title}" (${rollupColumn.uidt}) in "${relatedTable.title}" cannot be aggregated by a rollup.` +
      (aggregatable.length ? ` Aggregatable fields are: ${aggregatable.join(', ')}.` : ''),
  );
}
// :529–548 — circular lookup walk (must run AFTER refContext for cross-base):
if (columnId) {
  let lkCol = payload as LookupColumnReqType;
  while (lkCol) {
    if (columnId === lkCol.fk_lookup_column_id)
      NcError.get(context).badRequest('Circular lookup reference not allowed');
    lkCol = await Column.get(refContext, { colId: lkCol.fk_lookup_column_id })
      .then((c) => (c && c.uidt === 'Lookup') ? c.getColOptions<LookupColumn>(refContext) : null);
  }
}
```

**Flow:** ROLLUP: params → relation column exists → `isLinksOrLTAR` gate ("A rollup must aggregate through a link field") → resolve far-side column per shape (hm reads fk_child_column_id; mm/bt read fk_parent_column_id — the `isMMOrMMLike ? 'mm'` override forces junction columns down the bt/mm arm even when stored type differs) → target exists → aggregatable-type gate with SUGGESTIVE error listing eligible fields → function-vs-uidt availability gate. LOOKUP: params → relation → CIRCULARITY walk first (self-id equality anywhere in the chain throws) → far-side resolution adds an 'oo' case reading `column.meta?.bt` to pick parent vs child endpoint → membership check.
**Invariant:** The circular check needs `refContext` from the RELATION's options before walking — comment :529 "must be done after getting refContext for cross-base" (the chain may traverse into another base). Error messages embed candidate field lists — they're API contract, not logging.
**Probe:** `grep -c "Circular lookup reference not allowed" packages/nocodb/src/helpers/columnHelpers.ts` → `1`; `grep -c "Aggregatable fields are" packages/nocodb/src/helpers/columnHelpers.ts` → `1`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "validateRollupPayload validateLookupPayload", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ladder order (existence→shape-gate→aggregatability→function-availability), the mm override, refContext-first circularity, and exact error strings; adapt SDK type predicates.
