<!-- capsule-v2 -->
# Polymorphic list-payload guards — How can one API accept entities, enrichment tuples, batch tuples, and collections safely?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** how does one action endpoint validate four different caller payload shapes without duplicating rule logic?

## Four-shape union with one shared suffix validator
**Path/Symbol:** `core/public-methods/shared-types/listData/guards.js` — `areAllAdditionalParametersValid` (30–35), `isPlatformValid`/`isCollectingScopeValid`/`isCollectValid` helpers (20–29), per-entity tuple loops `isOrganizationsWithCollectInfoTargetStateAndPlatformAndCollectingScope` (36–51) / `isPeopleWithCollectInfoTargetStateAndPlatformAndCollectingScope` (68–86), one-batch variants (52–61, 87–99), union dispatchers `isIOrganizationsListData` (62–67) / `isIListData` (100–107).
**Signature:** `areAllAdditionalParametersValid(collect, targetState, overridePlatform, collectingScope): boolean`; `isIListData(data): boolean`.
**Data Shape:** shape 1 = iterable of entities; shape 2 = iterable of tuples `[entity, collect?, targetState?, overridePlatform?, collectingScope?]` (persons append `invitedPlatform?, messagedPlatform?, prevPlatform?`; destructured positionally); shape 3 = ONE batch tuple `[entities[], collect?, ...]`; shape 4 = Collection object. Entity slots accept a full aggregate OR a bare `DBId` (deferred reference); `collect` accepts `null | ICollectInfo | DBId`.

### Decisive source
```js
function isCollectValid(collect) {
    return collect === null || isICollectInfo(collect) || isDBId(collect);   // defer collect as rowid
}
function areAllAdditionalParametersValid(collect, targetState, overridePlatform, collectingScope) {
    return (isCollectValid(collect) &&
        isActionTargetStateOrUndefined(targetState) &&
        isPlatformValid(overridePlatform) &&        // nullish OR linkedin|salesNavigator|recruiter|talent
        isCollectingScopeValid(collectingScope));   // nullish OR {id, type: group-id|event-id}
}
// per-entity tuple shape — positional destructure, every element checked
const [person, collect, targetState, overridePlatform, collectingScope,
       invitedPlatform, messagedPlatform, prevPlatform] = personWithCollectInfo;
if (!(((isIPerson)(person) || isDBId(person)) &&
      areAllAdditionalParametersValid(collect, targetState, overridePlatform, collectingScope) &&
      isPlatformValid(invitedPlatform) && isPlatformValid(messagedPlatform) &&
      isPlatformValid(prevPlatform))) return false;
// union dispatcher — order matters only for clarity, all branches boolean
function isIListData(data) {
    return isPeople(data) ||
        isPeopleWithCollectInfoTargetStateAndPlatformAndCollectingScope(data) ||
        isPeopleWithOneCollectInfoTargetStateAndStatePlatformsAndCollectingScope(data) ||
        isIPeopleCollection(data);
}
```

**Flow:** try iterable-of-tuples (validate EVERY element's entity slot + shared 4-slot suffix [+ person-only 3 platform slots]) -> else try single batch tuple (suffix once, entities as a whole) -> else Collection guard -> else bare entities iterable. Any failing element rejects the whole payload.
**Invariant:** the shared suffix validator is the SINGLE point of truth for optional parameters across all four shapes — adding a parameter means extending one function and the tuple destructures; person tuples carry platform history (invited/messaged/prev), org tuples deliberately do not.
**Probe:** `node -e` against dist module: batch tuple `[[123], null, undefined, 'linkedin', undefined, undefined, undefined, undefined]` -> `isPeopleWithOneCollectInfoTargetStateAndStatePlatformsAndCollectingScope(...) === true`; same with `targetState: 5` -> `false`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "areAllAdditionalParametersValid listData guards", limit: 10 });
```

## Verdict
Adopt the four-shape union + shared-suffix pattern whenever one endpoint serves interactive (single entity), bulk (tuples), batch (one call), and saved-set (collection) callers; adopt DBId deferral for expensive sub-objects. Adapt slot lists to your host's optional-parameter set. Omit LinkedIn platform vocabularies. Coverage: file fully indexed (no_recorded_issue); probes executed against shipped dist modules (no test runner exists in this ingest).