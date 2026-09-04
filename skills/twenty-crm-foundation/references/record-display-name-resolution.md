<!-- capsule-v2 -->
# record-display-name-resolution — How is a human label derived for any record without knowing its schema?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** What is the labelIdentifier fallback ladder for record display names?

## record-display-name-resolution
**Path/Symbol:** `packages/twenty-server/src/engine/core-modules/record-crud/utils/get-record-display-name.util.ts:getRecordDisplayName` (:10-45).
**Signature:** `(record: Record<string, unknown>, flatObjectMetadata: FlatObjectMetadata, flatFieldMetadataMaps: FlatEntityMaps<FlatFieldMetadata>): string`.
**Data Shape:** input record may be partial; output is ALWAYS a non-empty string (id-based fallbacks guarantee it).

### Decisive source
```ts
if (labelIdentifierField.type === FieldMetadataType.FULL_NAME) {
  const nameValue = fieldValue as { firstName?: string; lastName?: string } | undefined;
  const firstName = nameValue?.firstName ?? '';
  const lastName = nameValue?.lastName ?? '';
  return `${firstName} ${lastName}`.trim() || String(record.id) || 'Unknown';
}
return isDefined(fieldValue)
  ? String(fieldValue)
  : String(record.id ?? 'Unknown');
```
(:32-44 — FULL_NAME gets special composition; everything else stringifies or falls back to id.)

**Flow:** read `labelIdentifierFieldMetadataId` from object metadata → missing id OR unresolvable field metadata ⇒ `String(record.id ?? 'Unknown')` → resolve the labeled field's value → FULL_NAME ⇒ "first last" trimmed, empty ⇒ id ⇒ value stringify with id fallback. In-source note (:9): this MIRRORS the frontend's `getLabelIdentifierFieldValue` — server and client must render the same label.
**Invariant:** never return an empty string; never throw on partial records. The mirror rule means a porter must keep server and client ladders in lockstep or UI labels will diverge from API references.
**Probe:** `grep -c 'Mirrors frontend' packages/twenty-server/src/engine/core-modules/record-crud/utils/get-record-display-name.util.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "getRecordDisplayName labelIdentifier", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the total-function display-name ladder (metadata-missing → id; value-missing → id; never empty). Adapt the special-cased composite types to your domain (FULL_NAME here). Keep a frontend/backend parity test if your product renders labels in both.
