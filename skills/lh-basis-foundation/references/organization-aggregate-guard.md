<!-- capsule-v2 -->
# Organization aggregate guard — How does a second, smaller aggregate family reuse the duck-typing recipe without inventing a new one?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** when a second domain aggregate is far simpler than the first, what stays invariant in its runtime guard and what scales?

## Org = dbItem ∧ property whitelist ∧ method surface (7/7)
**Path/Symbol:** `core/public-methods/models/organizations/Organization/guards.js` — `isIOrganization` (10–30), `isOrganizations` (31–41). Helpers: `helpers/guards/objects.js:objectHasProperties` / `objectHasMethods`; root `dbItem/guards.js:isIDBItem`.
**Signature:** `isIOrganization(value): boolean`; `isOrganizations(data): boolean`.
**Data Shape:** a valid organization = DB row (`id>0`) + **7 whitelisted properties** (`originalId`, `externalIds`, `miniProfile`, `extra`, `industries`, `specialities`, `tags`) + **7 named methods** (`addExternalIdentifier`, `setMiniProfile`, `setExtra`, `setSpecialities`, `setIndustries`, `addTag`, `removeTag`). Compare the person twin's 37 props / 45 methods.

### Decisive source
```js
function isIOrganization(value) {
    return (isIDBItem(value) &&
        objectHasProperties(value, [
            'originalId', 'externalIds', 'miniProfile',
            'extra', 'industries', 'specialities', 'tags',
        ]) &&
        objectHasMethods(value, [
            'addExternalIdentifier', 'setMiniProfile', 'setExtra',
            'setSpecialities', 'setIndustries', 'addTag', 'removeTag',
        ]));
}
function isOrganizations(data) {
    if (!isIterableData(data)) return false;
    for (const org of data) {
        if (!isIOrganization(org) && !isDBId(org)) return false;   // deferrable reference per element
    }
    return true;
}
```

**Flow:** dbItem check -> every whitelisted property must exist (presence, value unchecked) -> every named method must be callable -> collections validate element-wise with bare DBId allowed as a deferred reference.
**Invariant:** the RECIPE is family-invariant — `dbItem ∧ props ∧ methods` — only the lists scale with entity richness (person 37/45 vs org 7/7). A porter porting "the aggregate guard pattern" ports one composition and swaps lists; they must NOT weaken the method-surface check for the smaller family (a mini/org object missing `removeTag` is not an Organization even though all 7 fields exist).
**Probe:** `node -e` against shipped dist module: fixture `{id:1}` + 7 props null + 7 no-op methods → `true`; drop one method → `false`; `isOrganizations([fixture, 77])` → `true` (DBId element ok); `isOrganizations([{id:1}])` → `false`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.models.organizations.Organization.guards.isIOrganization" });
```

## Verdict
Adopt recipe-invariant aggregate guards: one composition, per-family lists, method surface mandatory at every size. Adapt property/method vocabulary to your domain. Omit LinkedIn field names. Coverage: no_recorded_issue + metadata_match @ gen 2026-08-23T00:11:49Z; probe executed against shipped dist module (no test runner exists in this ingest — standing block).
