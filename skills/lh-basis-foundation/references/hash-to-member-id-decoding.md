<!-- capsule-v2 -->
# Hash → memberId decoding — How do I recover a stable numeric member id from an opaque profile hash?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** how can two identifiers of the same person be reconciled when one surface only exposes the hash?

## `Type.Hash` decode ladder
**Path/Symbol:** `core/public-methods/models/people/PersonExternalIdentifier/IPersonExternalIdentifier.js` — `Hash.isValidHashString` (37–43 region of Type.Hash block), `Hash.extractExistingMemberId`, `Hash.extractMemberId`, `Hash.extractMemberIdData`; helpers `core/public-methods/models/helpers/guards/strings.js:isStringInBase64UrlEncoding` and `core/public-methods/models/helpers/utils/strings.js:getBase64FromBase64URL` (lines 8–11).
**Signature:** `isValidHashString(s: string): boolean`; `extractExistingMemberId(externalId: string): number`; `extractMemberId(externalId: string): number | null`; `extractMemberIdsData(identifiers[]): Map<memberId, {externalId:'<id>', type:'member-id', memberId, actualAt?}>`.
**Data Shape:** valid hash = base64url charset `/^[A-Za-z0-9_-]+$/` AND length exactly **39** AND 3-char prefix ∈ **['ACo','ACw','AEE','AEM','AAE']**; decoded payload bytes 4..8 hold the memberId as big-endian uint32.

### Decisive source
```js
Hash.VALID_PREFIXES = ['ACo', 'ACw', 'AEE', 'AEM', 'AAE'];
function isValidHashString(externalId) {
    if (typeof externalId === 'string' && isStringInBase64UrlEncoding(externalId)) {
        return (externalId.length === 39 &&
                Hash.VALID_PREFIXES.includes(externalId.slice(0, 3)));
    }
    return false;
}
function extractExistingMemberId(externalId) {
    return Buffer.from(getBase64FromBase64URL(externalId), 'base64').readUInt32BE(4);
}
function extractMemberId(externalId) {
    try { if (isValidHashString(externalId)) return extractExistingMemberId(externalId); } catch {}
    return null;                                  // silent-null policy
}
function getBase64FromBase64URL(base64URLString) {
    const paddingLength = 4 - (base64URLString.length % 4);
    return base64URLString.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat(paddingLength);
}
```

**Flow:** charset check -> length 39 + prefix whitelist -> base64url→base64 (charset swap + padding math `4 - len % 4`) -> Buffer decode -> `readUInt32BE(4)` -> memberId; `extractMemberIdsData` folds an identifier list into a Map keyed by memberId (dedup by construction), carrying `actualAt` through when present.
**Invariant:** decode is total — every failure path returns `null`, never throws; only *validated* hashes reach the Buffer step.
**Probe:** `node -e "const P=require('<root>/core/public-methods/models/people/PersonExternalIdentifier/IPersonExternalIdentifier.js').IPersonExternalIdentifier.Type.Hash; console.log(P.isValidHashString('ACoAAAXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'), P.extractMemberId('ACoAAAXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'))"` (39-char ACo… string with known embedded id).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.models.people.PersonExternalIdentifier.IPersonExternalIdentifier" });
```

## Verdict
Adopt validate-then-decode with silent-null semantics wherever an opaque vendor id secretly embeds a stable key. Adapt byte offset/endian to your actual payload layout (verify against real hashes before trusting offset 4). Omit the specific LinkedIn prefixes in non-LinkedIn hosts; keep citations-only (proprietary). Coverage note: no unit tests exist in this ingest — probes above were executed against the shipped dist modules.