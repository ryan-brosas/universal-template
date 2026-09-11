<!-- capsule-v2 -->
# Organization external identifiers — How does the second identity family scale the person pattern down to two wire types?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** when an entity has few identity surfaces, how much of the person identifier machinery survives?

## Two-type enum + mirrored numeric field
**Path/Symbol:** `core/public-methods/models/organizations/OrganizationExternalIdentifier/guards.js` — data validators `isIOrganizationPublicIdExternalIdentifierData` (15–21) / `isIOrganizationCompanyIdExternalIdentifierData` (22–30), union `isIOrganizationExternalIdentifierData` (31–33), DB composites (34–42), `convertOrganizationExternalIdentifierToString` (43–52); `enums.js:OrganizationExternalIdentifierTypes` = COMPANY_ID:'company-id', PUBLIC_ID:'public-id'.
**Signature:** `isIOrganizationExternalIdentifier(arg): boolean`; `isIOrganizationCompanyIdExternalIdentifierData(data): boolean`; `convertOrganizationExternalIdentifierToString(id): string | null`.
**Data Shape:** company-id rows carry a MIRRORED numeric field `companyId:number` alongside `externalId:string` — same denormalization discipline as person member ids (`memberId === Number(externalId)`).

### Decisive source
```js
function isIOrganizationCompanyIdExternalIdentifierData(data) {
    const arg = data;
    return Boolean(arg &&
        arg.externalId &&
        typeof arg.externalId === 'string' &&
        arg.type === OrganizationExternalIdentifierTypes.COMPANY_ID &&
        typeof arg.companyId === 'number' &&      // mirror field must be real number...
        !isNaN(arg.companyId));                   // ...and not NaN
}
function isIOrganizationExternalIdentifier(arg) {
    return isIDBItem(arg) && isIOrganizationExternalIdentifierData(arg) && isISentAtToPASDates(arg);
}
function convertOrganizationExternalIdentifierToString(id) {
    switch (id.type) {
        case OrganizationExternalIdentifierTypes.PUBLIC_ID:
        case OrganizationExternalIdentifierTypes.COMPANY_ID:
            return String(id.externalId);
        default:
            return null;                          // total: unknown type -> null, never throw
    }
}
```

**Flow:** data-level OR-dispatch on type (public-id: non-empty string externalId | company-id: additionally numeric companyId mirror) -> composite adds dbItem row shape ∧ PAS date block -> serialization switch returns `String(externalId)` or null default. PAS date block (`helpers/guards/dates.js`): `createdAt`, `updatedAt`, **`actualAt`** must ALL be `instanceof Date`; only `sentAtToPAS` is optional (Date or undefined) — omitting `actualAt` fails validation even though it looks optional by name.
**Invariant:** the family recipe is IDENTICAL to people (data validator ∧ dbItem ∧ timestamps) even though the taxonomy shrank 10 -> 2; mirrored numeric companions are validated as numbers, never re-parsed from the string at guard time.
**Probe:** `node -e` against dist guards: composite `{id:1, externalId:'acme', type:'public-id', createdAt:new Date(), updatedAt:new Date(), actualAt:new Date()}` -> true; SAME fixture WITHOUT `actualAt` -> **false** (four-field PAS block); `sentAtToPAS:'2026-01-01'` (string) -> false; `{externalId:'x', type:'company-id', companyId:'7'}` -> **false** (string mirror rejected); `companyId:7` -> true; convert `{externalId:'42', type:'company-id'}` -> `'42'`, unknown type -> null. All observed live against shipped dist modules.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", name_pattern: ".*OrganizationExternalIdentifier.*", limit: 14 });
```

## Verdict
Adopt the per-family recipe (taxonomy enum + OR-dispatched data validators + dbItem/timestamp composite + total serializer) for every new identity surface instead of growing one god-validator. Adapt type names and mirror fields. Omit LinkedIn id vocabularies. Coverage: no_recorded_issue on both cited files; probes executed against shipped dist modules (no test runner in ingest).
