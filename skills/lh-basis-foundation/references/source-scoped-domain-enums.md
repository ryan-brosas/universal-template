<!-- capsule-v2 -->
# Source-scoped domain enums — Where do platform taxonomies and conditional fields diverge per acquisition source?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** how do you encode a schema field that is only legal for SOME values of a sibling discriminator?

## Tri-state conditional field + inline taxonomies
**Path/Symbol:** `core/public-methods/models/collectInfo/guards.js` — `isCollectSource` (11–17), `isICollectingScope` (18–20), `isICollectInfo` (21–34); `core/public-methods/models/actions/TargetPlatform/guards.js:isTargetPlatform` (6–8, taxonomy INLINE — no enums file); `core/public-methods/models/actions/ActionVersion/enums.js:ActionTargetState` (6–6) + `guards.js` (`isActionTargetState` 8–10, `isActionTargetStateOrUndefined` 11–13).
**Signature:** `isICollectInfo(value): boolean`; `isICollectingScope(v): v is {id: string, type: 'group-id'|'event-id'}`; `isActionTargetStateOrUndefined(v): boolean`.
**Data Shape:** CollectSource = linkedin | salesNavigator | recriter… precisely: `'linkedin'|'salesNavigator'|'recruiter'|'talent'|'other'` ('other' exists ONLY here, not in TargetPlatform). Scope = `{id: non-empty string, type: 'group-id'|'event-id'}`. ActionTargetState reverse-keyed enum: Removed=-1, AddedManually=1, AddedByPrevAction=2.

### Decisive source
```js
function isTargetPlatform(value) {           // taxonomy lives in the guard itself
    return ['linkedin', 'salesNavigator', 'recruiter', 'talent'].includes(value);
}
function isICollectInfo(value) {
    if (isIDBItem(value)) {
        const { source, createdAt, collectingScope } = value;
        if (isCollectSource(source) && createdAt instanceof Date) {
            if (source === 'linkedin') {
                // tri-state: explicit null, absent, or a VALID scope object
                return collectingScope === null || collectingScope === undefined || isICollectingScope(collectingScope);
            } else {
                return collectingScope === undefined;   // other sources: strictly absent, NOT null
            }
        }
    }
    return false;
}
function isActionTargetState(value) { return Object.values(ActionTargetState).includes(value); }
```

**Flow:** dbItem shape check -> source must be a known CollectSource and createdAt a real `Date` -> branch ON SOURCE: linkedin permits tri-state collectingScope, every other source demands the key be `undefined` (passing explicit `null` for salesNavigator FAILS validation).
**Invariant:** discriminated-union legality is enforced at the OBJECT level, not the field level — a field value that is well-formed in isolation (null) can still be illegal because of a sibling field; enum membership checks use `Object.values(...).includes` so reverse-keyed numeric enums (including -1) work unmodified.
**Probe:** `node -e` against dist guards: `{id:1, source:'linkedin', createdAt:new Date(), collectingScope:null}` -> true; same with `source:'salesNavigator'` -> **false**; with `collectingScope:{id:'g1',type:'group-id'}` under linkedin -> true; `isTargetPlatform('salesNavigator')` true, `'other'` false; `isActionTargetState(-1)` true, `0` false.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.models.collectInfo.guards.isICollectInfo" });
```

## Verdict
Adopt source-branch validation for discriminator-conditional fields and keep small closed taxonomies INLINE in their guard when no other module needs the value list. Adapt scope kinds and source names to your host. Omit PAS date semantics. Watch the null-vs-undefined asymmetry: porters who normalize absent to null will silently break non-linkedin rows. Coverage: files indexed no_recorded_issue; probes executed against shipped dist modules (no test runner in ingest).