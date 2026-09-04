<!-- capsule-v2 -->
# param-metadata-coercion-dispatch — How does a formula function know each argument's field type at SQL-emit time?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What metadata thread drives per-call coercion in the db-provider function emitters?

## setCallMetadata around every emit; resolveFormulaParamInfo classifies each slot
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/sql-conversion.visitor.ts:visitFunctionCall` (:499-508 set + :825 clear) / `visitBinaryOp` (:832/:957) / `buildParamMetadata`; consumer `apps/nestjs-backend/src/db-provider/utils/formula-param-metadata.util.ts:resolveFormulaParamInfo` (:27-66) + predicates `isTrustedNumeric`/`isTextLikeParam`/`isDatetimeLikeParam`/`isBooleanLikeParam`/`isJsonLikeParam`.
**Signature:** `formulaQuery.setCallMetadata(metadata: IFormulaParamMetadata[] | undefined)`; `resolveFormulaParamInfo(metadataList, index?): IResolvedFormulaParamInfo`.
**Data Shape:** `IResolvedFormulaParamInfo { hasMetadata, type?, isFieldReference, isMultiValueField, isJsonField, fieldDbName?, fieldDbType?, fieldCellValueType? }`; lookup+json fields are forced `isJsonField && isMultiValueField`.

### Decisive source
```ts
const paramMetadata = exprContexts.map((exprCtx) => this.buildParamMetadata(exprCtx));
this.formulaQuery.setCallMetadata(paramMetadata);
try { ... } finally { this.formulaQuery.setCallMetadata(undefined); }
...
// util:
if (field?.isLookup && field.dbFieldType === DbFieldType.Json) {
  info.isJsonField = true;
  info.isMultiValueField = true;
}
if (!info.type) info.type = inferTypeFromField(field);
```

**Flow:** visitor collects per-argument AST context → builds `{type, isFieldReference, field…}` records → pushes them onto the shared formulaQuery → EVERY emitter (sum/if/tzWrap/looseNumericCoercion…) reads its slot's info to choose cast vs guard vs raw → metadata cleared in finally so later sibling calls can't inherit stale slots.
**Invariant:** metadata is STRICTLY call-scoped; a missing clear leaks one argument's coercion into unrelated functions (the exact bug class the try/finally guards). Lookup-json promotion means coercers treat any lookup as potentially-multi json without trusting cellValueType.
**Probe:** upstream direct specs drive this thread end-to-end (`select-query.postgres.spec.ts` sets `setCallMetadata([...])` then asserts emitted SQL contains BTRIM/CASE guards; same pattern in `generated-column-query.postgres.spec.ts`). Static probe byte-exact: `grep -n 'setCallMetadata(undefined)' sql-conversion.visitor.ts` → :397/:825/:957.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"setCallMetadata","limit":5,"detail":"ids"}'
```

## Verdict
Adopt scoped call-metadata as the coercion channel. Adapt the record shape. Omit nothing — the finally-clear discipline is the porting trap.
