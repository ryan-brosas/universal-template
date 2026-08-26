<!-- capsule-v2 -->
# Organization unique-id normalization — What happens when the dedup-key pipeline is FAIL-OPEN instead of fail-closed?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** the person kernel normalizes identities to `${group}:${externalId}` and fails closed on unknown types — what changes when an org twin deliberately does NOT?

## Identity-fallthrough type mapping + raw-string key derivation
**Path/Symbol:** `core/public-methods/models/organizations/OrganizationExternalIdentifier/IOrganizationExternalIdentifier.js` — `TypeGroup.fromType` (36–45), `UniqueId.fromExternalIdWithTypeOrTypeGroup` (67–81), `UniqueId.fromExternalId` (82–100).
**Signature:** `TypeGroup.fromType(type): string`; `UniqueId.fromExternalIdWithTypeOrTypeGroup(data | data[]): string | string[]`; `UniqueId.fromExternalId(idStr: string): string | undefined`.
**Data Shape:** same `${typeGroup}:${externalId}` grammar as persons (`company:...`, `public:...`); org groups are exactly `['company','public']`.

### Decisive source
```js
function fromType(type) {
    if (Type.Company.is(type)) return 'company';
    if (Type.Public.is(type))  return 'public';
    return type;                                   // UNKNOWN types pass through UNCHANGED — fail-open
}
function fromExternalId(data) {
    if (Array.isArray(data)) { /* map + collect */ }
    else {
        const externalIds = convertIdStrToDLIdentifiers(data);
        if (externalIds.length) {
            return fromExternalIdWithTypeOrTypeGroup(externalIds[0]);   // first classification wins
        }
    }                                              // unclassifiable -> implicit undefined, no throw
}
```

**Flow:** raw id STRING → regex classification (`convertIdStrToDLIdentifiers`) → take element [0] → type→group mapping (identity fallthrough for unknowns) → template into the dedup key. Array input maps per element. Contrast: the PERSON twin's group dispatch throws inside try/catch on unknown groups so validation returns `false`; here an unknown type flows straight into the output string.
**Invariant:** org normalization NEVER rejects — it either produces a key or returns `undefined`. That is safe only because org has exactly two closed patterns feeding it; porting this posture to a family with open-ended types silently produces bogus keys like `'weird-type:123'` where the person-style guard would have refused. Choose failure posture per family trust level, not globally.
**Probe:** `node -e`: `fromExternalId('12345')` → `'company:12345'`; `fromExternalId('some-co')` → `'public:some-co'`; `fromExternalId('!!!')` → `undefined`; `fromType('mystery')` → `'mystery'` (passthrough observed); array input → array of keys.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.models.organizations.OrganizationExternalIdentifier.IOrganizationExternalIdentifier.UniqueId.fromExternalId" });
```

## Verdict
Adopt fail-open normalization ONLY behind a closed classifier; keep the fail-closed person-style dispatch wherever types are user-supplied or open-ended. Adapt group vocabulary. Omit LinkedIn id grammars. Coverage: no_recorded_issue @ gen 2026-08-23T00:11:49Z; probe executed against shipped dist module (no test runner in ingest — standing block). Companion capsules: dl-identifier-conversion (classifier internals), external-identifier-type-algebra (fail-closed person twin).
