<!-- capsule-v2 -->
# DL identifier classification — How do you turn an opaque id STRING into a typed identifier without throwing on garbage?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** given a raw external-id string of unknown kind, what classification order, mirror field, and failure posture should a converter have?

## Regex classify → at most one identifier → empty array, never throw
**Path/Symbol:** `core/public-methods/models/organizations/OrganizationExternalIdentifier/utils.js` — `convertIdStrToDLIdentifiers` (8–24); `regex.js` — `ORGANIZATION_PUBLIC_ID_RX` (6), `ORGANIZATION_COMPANY_ID_RX = /^\d+$/` (7); `enums.js` — COMPANY_ID:'company-id', PUBLIC_ID:'public-id' (6–10).
**Signature:** `convertIdStrToDLIdentifiers(idStr: string, publicRegExp?: RegExp): Array<{type, externalId, companyId?}>`.
**Data Shape:** returns 0 or 1 identifier objects. company-id carries the denormalized mirror `companyId: Number(idStr)`; public-id does not.

### Decisive source
```js
function convertIdStrToDLIdentifiers(idStr, publicRegExp) {
    const identifiers = [];
    if (ORGANIZATION_COMPANY_ID_RX.test(idStr)) {            // /^\d+$/ — numeric branch FIRST
        identifiers.push({
            type: OrganizationExternalIdentifierTypes.COMPANY_ID,
            externalId: idStr,
            companyId: Number(idStr),                        // mirror invariant, same as memberId twins
        });
    }
    else if ((publicRegExp || ORGANIZATION_PUBLIC_ID_RX).test(idStr)) {
        identifiers.push({ type: OrganizationExternalIdentifierTypes.PUBLIC_ID, externalId: idStr });
    }
    return identifiers;                                      // possibly EMPTY — no throw
}
```

**Flow:** test the NARROW unambiguous pattern first (`^\d+$` company ids) -> else fall to the wide fuzzy pattern (unicode-property-rich public-slug regex allowing letters, emoji classes, `&.~-'`, digits) which the caller may OVERRIDE via the second argument -> unclassifiable input yields `[]`.
**Invariant:** precedence is correctness-critical — a pure-digit string must classify as company-id before the permissive public pattern ever sees it; and the mirror field (`companyId`) is populated at construction from the same string, keeping the `externalId === String(companyId)` consistency the guards enforce later. Failure is silent-and-empty by design so batch imports can skip junk rows instead of aborting.
**Probe:** `node -e`: `'12345'` → `[{type:'company-id', externalId:'12345', companyId:12345}]`; `'some-co'` → public-id without companyId; `'!!!'` → `[]` (no throw); custom `publicRegExp=/^x$/` makes `'x'` classify public while default regex would reject it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.models.organizations.OrganizationExternalIdentifier.utils.convertIdStrToDLIdentifiers" });
```

## Verdict
Adopt narrow-then-wide classification with an injectable wide pattern and empty-array failure for import-tolerant converters; populate denormalized mirrors at construction time. Adapt patterns to your id grammar. Omit the LinkedIn-specific unicode slug alphabet (keep the injectability). Coverage: no_recorded_issue ×3 @ gen 2026-08-23T00:11:49Z; probe executed against shipped dist module (no test runner in ingest — standing block).
