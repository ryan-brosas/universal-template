<!-- capsule-v2 -->
# Structural duck-type guards — how do I validate deserialized domain objects at a trust boundary without schemas?

**Source:** lh-basis NO-LICENSE extract — patterns only, never copy code (`core/public-methods/models/**`, compiled JS); Codebase Memory `lh-basis` (public-methods plane outside indexed roots → source-read probes). **Question:** how does the Linked Helper domain layer decide "this is a valid Person/Organization/collection" for data arriving from disk/network?

## The guard kit
**Path/Symbol:** `models/helpers/guards/objects.js` (isObject/objectHasProperties/objectHasStringProperties/objectHasNotEmptyStringProperties/objectHasNoProperties/objectHasMethods/isNullish); `models/dbItem/guards.js:isIDBItem/isDBId`; entity guards `models/people/Person/guards.js:isIPerson/isPeople`, `organizations/Organization/guards.js:isIOrganization/isOrganizations`; composite `shared-types/listData/guards.js:isIListData` family; primitives in `helpers/guards/iterable.js` + `numbers.js`.
**Signature:** `objectHasProperties(obj, props)` = every prop is `in obj` (presence, NOT type); `objectHasMethods(instance, names)` = present AND `typeof === 'function'`; `isDBId(id)` = number && !NaN && > 0; entity guard = `isIDBItem(value) && objectHasProperties(value, [...30 props]) && objectHasMethods(value, [...33 methods])`.
**Data Shape:** guards accept REAL entities or bare DB ids interchangeably (`isIPerson(person) || isDBId(person)`) — collections may hold hydrated rows or id references; `isPeople(iterable)` iterates and fails on the FIRST invalid member.

### Decisive source
```js
// presence-check + method-check + numeric-id = the whole trust model
function isIPerson(value) {
  return isIDBItem(value)
      && objectHasProperties(value, ['originalId','externalIds','miniProfile','memberDistance', /* ...30 total */])
      && objectHasMethods(value, ['getEmailActualAt','getSkillsActualAt','setPositions', /* ...33 total */]);
}
function isPeople(data) {
  if (!isIterableData(data)) return false;
  for (const person of data) {
    if (!isIPerson(person) && !isDBId(person)) return false;   // entity OR bare id, both legal
  }
  return true;
}
```

**Flow:** deserialized rows enter via source-carrying-model-serialization hydration → callers verify shape BEFORE use with one composed predicate instead of try/catch around property access → list-level guards fan the same check over iterables accepting entity-or-id unions → composite listData guards validate TUPLES `[organization, collect, targetState, overridePlatform, collectingScope]` where each slot has its own nullish-or-typed rule.
**Invariant:** property checks are PRESENCE-based (`prop in obj`) so optional/undefined values pass — the method-list is what proves behavior survived serialization (a plain JSON round-trip FAILS objectHasMethods by design: methods only exist on live class instances); ids must be positive numbers, not strings. Guards return booleans, NEVER throw — validation is a question, not an assertion.
**Probe:** no test files ship in this plane (coverage caveat) — deterministic probes: needle `objectHasProperties` + `'getEmailActualAt'` in `models/people/Person/guards.js`; graph probe returns 0 hits BY DESIGN (`lh-basis` excludes `core/local-source/dist`, public-methods sits outside both indexed roots) → direct source paths are the evidence.
**Retrieve:**
```
# graph does not cover this plane — retrieve by reading:
# lh-basis/core/public-methods/models/people/Person/guards.js
# lh-basis/core/public-methods/models/helpers/guards/objects.js
```

## Verdict
Adopt the pattern: presence+method two-list duck typing, positive-numeric-id gate, boolean-returning validators, entity-or-id union acceptance at collection boundaries. Adapt the property/method lists per host domain. Omit verbatim lists (no-license source — record shapes, retype from your own domain). Composes with source-carrying-model-serialization (hydration) as its validation counterpart.
