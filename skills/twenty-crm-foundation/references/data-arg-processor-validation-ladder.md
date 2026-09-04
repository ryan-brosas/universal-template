<!-- capsule-v2 -->
# data-arg-processor-validation-ladder — How are raw record inputs coerced per field type, and what is refused outright?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** What is the per-type validate/transform dispatch and its cross-cutting guards?

## data-arg-processor-validation-ladder
**Path/Symbol:** `packages/twenty-server/src/engine/api/common/common-args-processors/data-arg-processor/data-arg-processor.service.ts:DataArgProcessorService.process/processField` (:71-351).
**Signature:** `process({partialRecordInputs, authContext, flatObjectMetadata, flatFieldMetadataMaps, flatObjectMetadataMaps, shouldBackfillPositionIfUndefined=true}): Promise<Partial<ObjectRecord>[]>`; private `processField(fieldMetadata, key, value, ...): Promise<unknown>` — exhaustive switch with `assertUnreachable` default.
**Data Shape:** unknown input values in → validated + transformed values out; throws CommonQueryRunnerException INVALID_ARGS_DATA for unknown keys, missing metadata, non-nullable-without-default nulls.

### Decisive source
```ts
if (!isDefined(fieldMetadataId)) {
  throw new CommonQueryRunnerException(
    `Object ${flatObjectMetadata.nameSingular} doesn't have any "${key}" field.`,
    CommonQueryRunnerExceptionCode.INVALID_ARGS_DATA,
    { userFriendlyMessage: STANDARD_ERROR_MESSAGE },
  );
}
```
(:121-127 — every input key MUST resolve to real field metadata; no silent key dropping. Lookup covers BOTH `fieldIdByName` and relation join columns via `fieldIdByJoinColumnName`.)

**Flow:** position override FIRST (RecordPositionService over the whole batch, :100-110) → per record, per key: resolve field id (name or join-column) → throw on unknown → throw on `!defaultValue && !isNullable && null` (:143-153) → skip undefined → dispatch by type: POSITION re-validates overridden numbers (rejects NaN/±Infinity); RELATION/MORPH rejects ONE_TO_MANY writes entirely and requires connect/disconnect shape for non-join-column keys (:240-262); TS_VECTOR refuses writes (:339-344); SELECT/RATING validate against `options[].value`; composite types route through paired validate*OrThrow + transform* utils.
**Invariant:** exhaustive-switch compile safety (`assertUnreachable`) forces new field types to add a validator; the required-field check runs BEFORE transform so hostile payloads fail cheaply; connect.where values are recursively processed but ORIGINAL KEYS ARE PRESERVED by filtering the processed object against the original key set — "processField may add null subfields that alter WHERE semantics" (:416-425 comment is the invariant).
**Probe:** `grep -c "doesn't have any" packages/twenty-server/src/engine/api/common/common-args-processors/data-arg-processor/data-arg-processor.service.ts` → 1; direct spec coverage lives under `src/engine/api/common/common-args-processors/data-arg-processor/__tests__/` (validator-utils specs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "DataArgProcessorService processField", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt strict key-admission (unknown key = loud error), pre-transform required-field checks, write-refusal for computed/system types, and original-key preservation when processing nested where-values. Adapt the per-type validator set to your field taxonomy. Omit Twenty's specific composite transforms (currency/phone/rich-text) unless porting those domains too.
