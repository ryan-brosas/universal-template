<!-- capsule-v2 -->
# Storage-type mapping — which Postgres column type does each teable field type get, and why do autoNumber/link break the generic ladder?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** A porter recreating DDL from field metadata needs the exact cellValueType→dbFieldType ladder and its exceptions.

## value-type visitor delegation with three hard overrides
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/visitors/FieldStorageTypeVisitor.ts` — `setTypeFromValueType` (187–202), `resolveDbFieldType` (205–226), `visitAutoNumberField` (137–149), `visitLinkField` (155–166), module-level memoized `jsonSpecResult` (33–38); direct test `FieldStorageTypeVisitor.spec.ts` 'maps field types to v1 storage type strings' (:19).
**Signature:** `apply(table | fields): Result<void>` populates `typesById(): ReadonlyMap<string, {cellValueType, dbFieldType, isMultipleCellValue}>`.

### Decisive source
```ts
const resolveDbFieldType = (field, cellValueType, isMultipleCellValue): string => {
  if (isMultipleCellValue) return 'JSON';
  if (fieldIsJson(field)) return 'JSON';              // spec-based override, memoized spec ONCE at module scope
  switch (cellValueType) {
    case 'number':   return 'REAL';
    case 'dateTime': return 'DATETIME';
    case 'boolean':  return 'BOOLEAN';
    case 'string':   return 'TEXT';
    default:         return 'TEXT';                    // fail-open to TEXT
  }
};
// visitAutoNumberField: dbFieldType = isMultipleCellValue ? 'JSON' : 'INTEGER'   ← INTEGER, not REAL ("V1 parity")
// visitLinkField:      dbFieldType = 'JSON' unconditionally                       ← link cells store id arrays
```

**Flow:** every visit method delegates to `setValueTypeFromValueType` except autoNumber and link which pin their own dbFieldType; the visitor accumulates into `typesByFieldId` keyed by field-id string and returns a defensive COPY (`new Map(...)`) so callers can't mutate accumulated state.
**Invariant:** the ladder is checked in order multiplicity → json-spec → cellValueType; reordering breaks attachment/user fields (multiple → must be JSON even though cellValueType is string). autoNumber uses INTEGER because v1 wrote integers and REAL would change sort/coercion semantics across a mixed-version database. Unknown cellValueTypes fall OPEN to TEXT rather than erroring — DDL generation must never abort on an unmapped type.
**Probe:** `FieldStorageTypeVisitor.spec.ts` :19 asserts the full type→string map incl. the autoNumber INTEGER exception.
**Coverage:** fully indexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "FieldStorageTypeVisitor resolveDbFieldType setTypeFromValueType", limit: 8 });
```

## Verdict
Adopt the ladder + the two overrides verbatim (they encode cross-version data compatibility); adapt type-string vocabulary if the host DB differs; omit the v2-core visitor plumbing but keep the memoized-spec pattern to avoid rebuilding specs per field.
