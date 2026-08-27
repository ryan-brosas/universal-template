<!-- capsule-v2 -->
# Person aggregate guard — How do you duck-type a rich domain object by pinning BOTH its fields and its behavior?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** without classes or schemas, what makes an object "a Person" rather than a lookalike?

## Property whitelist + method-surface check
**Path/Symbol:** `core/public-methods/models/people/Person/guards.js` — `isIPerson` (10–98), `isPeople` (99–109). Helpers: `helpers/guards/objects.js:objectHasProperties` / `objectHasMethods`; root `dbItem/guards.js:isIDBItem`.
**Signature:** `isIPerson(value): boolean`; `isPeople(data): boolean`.
**Data Shape:** a valid person = DB row (`id>0`) + **37 whitelisted properties** (originalId, externalIds, miniProfile, memberDistance, networkInfo, connectionsInfo, currentPosition, email, tags, skills, interests, recommendations, positions, education, customFields, note, campaignsHistory, certifications, volunteers, languages, mutualTotal, badges, mutual, originalMutual, followers, address, birthday, connect, websites, twitters, messengers, phoneNumbers, thirdPartyEmails, industry, location, summary, …) + **45 named methods** (getEmailActualAt, addExternalIdentifier, setCustomMiniProfile, setMemberDistance, useCredits-style mutators, saveNote, removeTag, …).

### Decisive source
```js
function isIPerson(value) {
    return (isIDBItem(value) &&
        objectHasProperties(value, [
            'originalId', 'externalIds', 'miniProfile', 'memberDistance', /* ...37 total */
        ]) &&
        objectHasMethods(value, [
            'getEmailActualAt', 'getSkillsActualAt', 'addExternalIdentifier',
            'setOriginalMiniProfile', /* ...45 total */
        ]));
}
function isPeople(data) {
    if (!isIterableData(data)) return false;
    for (const person of data) {
        if (!isIPerson(person) && !isDBId(person)) return false;   // deferrable reference allowed per element
    }
    return true;
}
```

**Flow:** dbItem check -> EVERY whitelisted property must exist as own property (value may be null/undefined-ish; presence is what counts) -> EVERY named method must be present and callable -> collections validate element-wise with bare DBId allowed as a deferred reference.
**Invariant:** the guard pins BEHAVIOR, not just shape — an object missing one mutator (say `saveNote`) is not a Person even if all 37 fields exist; conversely field values are NOT type-checked here (deep value rules live in sub-guards like externalIds). Presence-checks make partial hydration representable.
**Probe:** `node -e`: build fixture programmatically — `{id:1}` + all 37 props set to null + all 45 methods as no-op arrows -> `isIPerson === true`; delete one prop -> false; replace one method with a non-function -> false; `isPeople([fixture, 77])` -> true (DBId element ok); `isPeople([{id:1}])` -> false.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.models.people.Person.guards.isIPerson" });
```

## Verdict
Adopt whitelist+methodsurface duck-typing when porting rich aggregates across process boundaries where instanceof is meaningless — it detects the wrong-fixture class of bug (mock objects missing mutators) that pure shape checks cannot. Adapt the property/method lists to your aggregate. Omit LinkedIn field vocabulary. Caveat: property PRESENCE is checked, not value types — pair with sub-guards per field family. Coverage: no_recorded_issue; probe executed against shipped dist module (no test runner in ingest).
