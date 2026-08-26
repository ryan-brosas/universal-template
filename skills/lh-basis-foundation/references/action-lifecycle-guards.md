<!-- capsule-v2 -->
# Action lifecycle guards — How is a family split enforced when the org variant has NO discriminator field at all?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** how do you tell a People action from an Organizations action when only one of the two guards carries any positive type check?

## Absence-only family split over a versioned, iterated lifecycle
**Path/Symbol:** `core/public-methods/models/actions/Action/guards.js` — `commonActionProperties` (9–31), `isIAction` (32–41), `isIOrganizationsAction` (42–46).
**Signature:** `isIAction(value): boolean`; `isIOrganizationsAction(value): boolean`.
**Data Shape:** dbItem (`id>0`) ∧ 20 common properties (`campaignId, versions, target, queued, processed, successful, excluded, failed, skipped, name, description, excludeList, config, isInProgress, isCompleted, startAt, currentIterationId, currentIterationResultsCount, order, isDeleted, postponeReason`). People adds `replied, messaged, pendingReview, actionLevelCustomFields`.

### Decisive source
```js
function isIAction(value) {
    return ((0, guards_1.isIDBItem)(value) &&
        (0, objects_1.objectHasProperties)(value, [
            ...commonActionProperties,
            'replied', 'messaged', 'pendingReview', 'actionLevelCustomFields',
        ]));
}
function isIOrganizationsAction(value) {
    return ((0, guards_1.isIDBItem)(value) &&
        (0, objects_1.objectHasProperties)(value, [...commonActionProperties]) &&
        (0, objects_1.objectHasNoProperties)(value, ['replied', 'messaged', 'pendingReview', 'actionLevelCustomFields']));
}
```

**Flow:** unlike campaigns (enum discriminator on `type`), an action's family is determined ENTIRELY by which engagement/custom-field keys exist: people = common + four extra keys; organizations = common ∧ those same four keys absent. There is no `actionType` enum check in either guard.
**Invariant:** the two guards are mutually exclusive (an object carrying `messaged` can never be an org action) but their union does NOT cover "action-shaped" objects missing optional keys — validation falsifies rather than coerces. Lifecycle fields show actions are versioned (`versions`) and iterated units (`currentIterationId`, `currentIterationResultsCount`, `startAt`, `order`) whose postponement is a typed slot (`postponeReason` — see postpone-reason-tagged-union).
**Probe:** deterministic node-require:
```bash
node -e "const g=require('/mnt/hdd/utopia/inspo/lh-basis/core/public-methods/models/actions/Action/guards.js');const c=['campaignId','versions','target','queued','processed','successful','excluded','failed','skipped','name','description','excludeList','config','isInProgress','isCompleted','startAt','currentIterationId','currentIterationResultsCount','order','isDeleted','postponeReason'].reduce((o,k)=>(o[k]=k==='versions'?[]:(k==='config'?{}:1),o),{id:7});const p={...c,replied:{},messaged:{},pendingReview:{},actionLevelCustomFields:{}};console.log(g.isIAction(p),g.isIOrganizationsAction(p),g.isIAction(c),g.isIOrganizationsAction(c))"
```
→ expect `true false false true` (the SAME core object flips family purely by adding/removing the four keys).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "action guard properties", file_pattern: "*actions/Action*", limit: 10 });
```
Observed pass 3: returns `isIAction` (32–41) / `isIOrganizationsAction` (42–46) atop the file's function set.

## Verdict
Adopt absence-based discrimination when legacy payloads cannot carry a family tag — but document the absence set explicitly; it is unguessable. Adapt key names; consider ADDING a positive discriminator when porting greenfield. Omit engine-side scheduling semantics behind `postponeReason`/`currentIterationId` (unindexed). Caveat: no upstream tests exist for this file (repo ships none for public-methods); evidence is direct source read + deterministic probe.
