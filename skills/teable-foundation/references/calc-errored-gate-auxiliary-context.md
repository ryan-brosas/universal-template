<!-- capsule-v2 -->
# Errored-field gate + lookup-context auxiliary — how does calculation skip broken fields while still loading the data their filters need?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Why do errored link fields get filtered at TWO stages, and why does createAuxiliaryData fetch fields that aren't in the dependency set?

## isErroredLinkField gates + createAuxiliaryData
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/link.service.ts:isErroredLinkField` (:85–88) used in `getDerivateByLink` :1706–1720 and `planDerivateByLink` :1756–1771; `apps/nestjs-backend/src/features/calculation/reference.service.ts:createAuxiliaryData` (:91–164) incl. `getLookupFilterFieldMap` (:66–90).
**Signature:** `createAuxiliaryData(allFieldIds): Promise<{fieldMap, fieldId2TableId, fieldId2DbTableName, dbTableName2fields, tableId2DbTableName}>`.
**Data Shape:** Extra context fields come from `field.lookupLinkedFieldId` (the link a lookup rides) and from `extractFieldIdsFromFilter(lookupOptions.filter, true)`.

### Decisive source
```ts
// if a field that has been looked up  has changed, the link field should be retrieved as context
const extraLinkFieldIds = difference(
  fieldRaws.filter((field) => field.lookupLinkedFieldId)
    .map((field) => field.lookupLinkedFieldId as string),
  allFieldIds
);
```
```ts
const linkContexts = linkLikeContexts.filter((ctx) => {
  const field = fieldMap[ctx.fieldId];
  if (!field) return false;
  if (this.isErroredLinkField(field)) return false;   // hasError flag → skip silently
  if (field.type !== FieldType.Link || field.isLookup) return false;
  return true;
});
```

**Flow:** Auxiliary assembly loads raws for the requested ids, then WIDENS with every link field that looked-up fields hang from and every field referenced inside lookup filters — because computing a lookup cell requires reading its filter's operands and riding its link, not just its own row. The graph is then re-filtered to fields that actually resolved (`validFieldIds`), dropping edges to soft-deleted fields before topo sort. Errored (`hasError`) link fields are excluded from derivation contexts so a broken field neither blocks nor corrupts sibling computation.
**Invariant:** Context-widening must happen BEFORE graph filtering/topo (a porter who trims to the seed set first computes lookups against missing filter operands); errored-field exclusion must NOT remove the field from metadata maps — only from active derivation — or diffs misreport.
**Probe:** `grep -cF 'lookupLinkedFieldId' apps/nestjs-backend/src/features/calculation/reference.service.ts` → 2; `grep -cF 'isErroredLinkField' apps/nestjs-backend/src/features/calculation/link.service.ts` → ≥5.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "createAuxiliaryData getLookupFilterFieldMap isErroredLinkField", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt widen-then-filter auxiliary assembly + hasError derivation gating; adapt your broken-field signal; omit filter extraction if lookups can't filter.
