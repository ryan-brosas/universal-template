<!-- capsule-v2 -->
# Field-DTO deserialization ladder — how do 20+ persisted field types (plus v1 conditional twins and corrupt options) become domain DTOs?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the canonical read path that turns raw field rows into typed persistence DTOs without ever failing the whole table load?

## Flag-trust base + per-type option coercion + v1 split shims
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresTableRepository.ts`: `deserializeFieldDto` (:1491-1843), base assembly (:1588-1609 incl. the flag-trust comment :1605), lookup resolution (:1519-1561: prefer `lookup_options`, fall back to legacy `options` fields, validate ids via FieldId/TableId.create), conditionalLookup v1 split (:1614-1637 + :1822-1837), conditionalRollup v1 options/config split (:1783-1821), per-type branches rating/singleSelect/multipleSelect/number/formula/rollup/longText/checkbox/attachment/date/createdTime/lastModifiedTime/user/createdBy/lastModifiedBy/autoNumber/button/link (:1635-1782), terminal fallback singleLineText (:1838-1842), `deduplicateSelectChoices` (:40-53).
**Signature:** private, row-typed input → `core.ITableFieldPersistenceDTO`.
**Data Shape:** unknown/unparseable options ⇒ undefined (or safe defaults: rating icon 'star'/max 5; rollup expression 'countall({values})'; formula `{expression:''}`); type string never trusted for conditional flags.

### Decisive source
```ts
const base = {
  ...baseCommon,
  // Trust the is_lookup flag from the database directly, regardless of whether
  // lookupOptions can be parsed
  ...(row.is_lookup ? { isLookup: true } : {}),
  ...(row.is_conditional_lookup && lookupOptions ? { isConditionalLookup: true } : {}),
};
if (row.is_conditional_lookup) {
  const conditionalOptions = hasLookupOptions ? buildConditionalLookupOptions(lookupParsed) : undefined;
  if (conditionalOptions) return { ...baseCommon, type:'conditionalLookup', options: conditionalOptions,
    innerType: row.type, innerOptions: asOptions<unknown>(), … };
}   // falls through to the plain-type branch when options are unparseable — degrade, don't fail
```

**Flow:** parse JSON columns tolerantly ({}) → build common base (flags only when true) → resolve lookup options with legacy fallback + id validation (invalid ⇒ undefined) → conditional branch first (carrying innerType/innerOptions), then per-type switches minting defaults for missing options → anything unrecognized degrades to singleLineText.
**Invariant:** A malformed row NEVER fails table hydration — worst case a field renders as text. The is_lookup flag survives even when its options payload is garbage so link topology remains visible for repair. Conditional twins preserve the ORIGINAL type as innerType because v2 stores them as their own field type while v1 stored the inner type + inline config.
**Probe:** mapping exercised across PostgresTableRepository.spec.ts + helpers spec suites; parse_partial flag = line 1224 only.
**Coverage caveat:** per-type defaults verified by source reading; spec coverage concentrates on select/link/lookup paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "deserializeFieldDto resolveLookupOptions normalizeSelectOptions deduplicateSelectChoices", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt degrade-don't-fail deserialization with flag-trust separation; adapt your type set; keep the innerType preservation when introducing new composite field types over legacy storage.
