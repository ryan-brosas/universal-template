<!-- capsule-v2 -->
# data-alias-nested / bulk-data-alias — NOT pure delegation: the alias surface carries its own ACL, sanitize, and payload-limit contracts

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory project `nocodb`. **Question:** Prior passes recorded the two alias services as "pure delegation over the mined funnel" — what do you LOSE if you port them as pass-throughs?

## Alias-nested: sanitizer + DESIGN NOTE + source asymmetry
**Path/Symbol:** `packages/nocodb/src/services/data-alias-nested.service.ts` (426L whole file; `mmList` :20-77, `hmList` :308-358, excluded family :79-305).
**Signature:** e.g. `async mmList(context: NcContext, param: PathParams & { query: any; columnName: string; rowId: string })`.
**Data Shape:** every list method: `getViewAndModelByAliasOrId` → `Source.get(model.source_id)` → `Model.getBaseModelSQL({viewId})` → `getColumnByIdOrName` → `restrictNestedLinkQueryForColumn(context, column, param.query)` → primitive fetch + count → `PagedResponseImpl(data, {count, ...param.query})`.

### Decisive source
```ts
// packages/nocodb/src/services/data-alias-nested.service.ts:28-34 — mmList's DESIGN NOTE
// NOTE: view-hidden columns stay queryable here and in the sibling
// nested-link methods below — field visibility is the column-level ACL,
// not view `show`, so we do NOT strip where/sort just because a column is
// hidden in the view (see the DESIGN NOTE in public-datas.service.ts).
// The `restrictNestedLinkQueryForColumn` calls below are a SEPARATE
// boundary: they gate on cross-base / no-visibility-access related tables,
// not on view `show`.
```
```ts
// :373-389 — relationDataAdd does NOT resolve Source; relationDataRemove does
const baseModel = await Model.getBaseModelSQL(context, {
  id: model.id,
  viewId: view?.id,
  dbDriver: await NcConnectionMgrv2.get(source),   // add(): no Source.get above
});
```
(Compare `relationDataRemove` :370-380, which resolves `source` first — a live asymmetry.)

## Bulk-alias: typed operation dispatcher with per-op option shaping
**Path/Symbol:** `packages/nocodb/src/services/bulk-data-alias.service.ts` (217L whole file; `executeBulkOperation` :32-46).
**Data Shape:** `BulkOperation = 'bulkInsert'|'bulkUpdate'|'bulkUpdateAll'|'bulkDelete'|'bulkUpsert'|'bulkDeleteAll'`; each public method shapes its OWN options tuple.

### Decisive source
```ts
// packages/nocodb/src/services/bulk-data-alias.service.ts:32-46
async executeBulkOperation<T extends BulkOperation>(
  context: NcContext,
  param: PathParams & {
    operation: T;
    options: Parameters<(typeof BaseModelSqlv2.prototype)[T]>;
  },
) {
  // ... getModelViewBase + getBaseModelSQL ...
  return await baseModel[param.operation].apply(null, param.options);
}
// :66 — API-token bulk cap, applied by FOUR of six methods (NOT UpdateAll/DeleteAll)
validateV1V2DataPayloadLimit(context, param);
// helpers/dataHelpers.ts:270-281: fires only for is_api_token + Array body
// exceeding V1_V2_DATA_PAYLOAD_LIMIT (constants/index.ts: NC_API_BULK_OPERATION_MAX_RECORDS
// || NC_DATA_PAYLOAD_LIMIT || 100)
```

**Flow (alias-nested):** identity resolution → LTAR type check (list methods only; excluded methods skip it) → mutate-in-place query sanitization → fetch+count read the SAME mutated query → paged envelope. **Flow (bulk-alias):** optional payload-limit gate → resolve model/view/source → generic `.apply` dispatch of the method-shaped options tuple.
**Invariant:** the alias layer owns three non-delegable duties — nested-link predicate confinement BEFORE both consumers, API-token bulk-record caps on interactive-shaped ops only, and TraceCommand op naming per endpoint (`recordLinkRemove/recordLinkAdd/recordBulk*`); dropping any of them changes the security/audit envelope even though the data path still works. `typecast` is parsed from `cookie.query.typecast === 'true'` in update/upsert only.
**Probe:** Direct tests are construction-only stubs at this pin: `bulk-data-alias.service.spec.ts:16 'should be defined'`; no behavioral spec exists. Deterministic probes: verbatim greps pinning `field visibility is the column-level ACL` (:29), `restrictNestedLinkQueryForColumn(context, column, param.query)` ×7, `apply(null, param.options)` (:45), and `validateV1V2DataPayloadLimit(context, param)` ×4; graph resolves `DataAliasNestedService.mmList … 20-77` and all seven BulkDataAliasService members.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DataAliasNestedService restrictNestedLinkQueryForColumn BulkDataAliasService executeBulkOperation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the alias layer as a real boundary (sanitize-before-consume, token-scoped bulk caps, per-endpoint trace ops, PagedResponse envelope). Adapt the option-tuple typing to your host's dispatch style. Omit: nothing from these two files — but CORRECT the prior pass record: they were mislabeled pure delegation; the "identical confinement discipline" peek was right about discipline but wrong about triviality. Coverage caveat: construction-only specs; deterministic probes only.
