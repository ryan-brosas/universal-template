<!-- capsule-v2 -->
# Cross-layer DB collision error mining — How do I detect a UNIQUE-constraint violation buried in ORM/driver error wrappers?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** when SQLite uniqueness surfaces through N wrapping layers (app error -> ORM -> driver), how does the top layer recognize it without coupling to every wrapper?

## Cycle-safe recursive error-chain walk
**Path/Symbol:** `core/public-methods/shared-types/sourceErrors/guards.js` — `findPersonMemberExternalIdCollisionErrorData` (15–36), `isPersonMemberExternalIdCollisionError` (12–14), `getPersonMemberExternalIdCollisionErrorData` (9–11); `constants.js:PERSON_MEMBER_EXTERNAL_ID_COLLISION_ERROR_CODE = 'PERSON_MEMBER_EXTERNAL_ID_COLLISION'`; producer `errors.js:class PersonMemberExternalIdCollisionError extends Error` (7–14).
**Signature:** `findPersonMemberExternalIdCollisionErrorData(error, visited = new Set()): error | null`; `isPersonMemberExternalIdCollisionError(error): boolean`.
**Data Shape:** marker error carries `code` (string constant) + `externalIds: string[]` (non-empty). Wrapper chain follows properties **data -> cause -> originalError -> driverError**.

### Decisive source
```js
class PersonMemberExternalIdCollisionError extends Error {
    constructor(data) {
        super('Person member external id collision');
        this.code = PERSON_MEMBER_EXTERNAL_ID_COLLISION_ERROR_CODE;   // stamp, don't rely on instanceof
        this.name = this.constructor.name;
        this.externalIds = data.externalIds;
    }
}
function findPersonMemberExternalIdCollisionErrorData(error, visited = new Set()) {
    if (!isObject(error)) return null;
    if (visited.has(error)) return null;          // cycle-safe: error.cause chains can loop
    visited.add(error);
    if (error.code === PERSON_MEMBER_EXTERNAL_ID_COLLISION_ERROR_CODE &&
        Array.isArray(error.externalIds) &&
        error.externalIds.length > 0 &&
        error.externalIds.every((externalId) => typeof externalId === 'string')) {
        return error;                              // full marker payload, not just true
    }
    for (const propertyName of ['data', 'cause', 'originalError', 'driverError']) {
        const nested = findPersonMemberExternalIdCollisionErrorData(error[propertyName], visited);
        if (nested) return nested;
    }
    return null;
}
```

**Flow:** producer stamps code+payload on the richest available layer -> consumer receives an opaque thrown/wrapped error -> walk descends through the four conventional wrapper properties depth-first -> first node satisfying code+shape wins and is RETURNED (caller reads `externalIds` off it) -> exhausted chain yields null.
**Invariant:** recognition never uses `instanceof` (wrappers clone/rebuild errors across layer boundaries); the visited Set makes self-referential `.cause` cycles terminate; a positive match requires the FULL payload shape, so a bare code string alone cannot spoof a match.
**Probe:** `node -e`: build `err = new Error('wrap'); err.data = { cause: { code: 'PERSON_MEMBER_EXTERNAL_ID_COLLISION', externalIds: ['ACoAAA','123'] } }` plus a self-referential `.self` loop -> `isPersonMemberExternalIdCollisionError(err) === true` and returned data `.externalIds` length 2; plain `Error` -> `false`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.shared-types.sourceErrors.guards.findPersonMemberExternalIdCollisionErrorData" });
```

## Verdict
Adopt stamped-code + payload markers and the four-property walk (extend the property list to your stack's wrappers, e.g. `errors[]`) for any storage-layer unique-violation that must survive ORM boundaries. Adapt the code constant and payload fields to your schema. Omit the LinkedIn-specific externalIds semantics. Coverage: all three files indexed no_recorded_issue; probe executed against shipped dist modules (no test runner in ingest).