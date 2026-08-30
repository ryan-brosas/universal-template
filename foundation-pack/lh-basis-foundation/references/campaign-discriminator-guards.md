<!-- capsule-v2 -->
# Campaign discriminator guards — How does the kernel validate its largest aggregate and split it into People vs Organizations variants?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** what makes an object a valid campaign, and how do the two family variants differ when they share one property list?

## Enum-split aggregate guard with a mirrored counter taxonomy
**Path/Symbol:** `core/public-methods/models/campaigns/guards.js` — `commonCampaignProperties` (10–33), `commonCampaignMethods` (34), `isICampaign` (35–41), `isIOrganizationsCampaign` (42–49); `core/public-methods/models/campaigns/enums.js` — `CampaignType` (6–10), `CampaignStates` (11–20), `CampaignSubListTypes` (21–35).
**Signature:** `isICampaign(value): boolean`; `isIOrganizationsCampaign(value): boolean`.
**Data Shape:** dbItem (`id>0`) ∧ 21 common properties (`actions, workQueue, type, createdAt, target, queued, processed, inProgress, successful, failed, excluded, skipped, exclude, name, description, isPaused, isReadonly, isHidden, isStandByModeActive, isValid, state, excludeList`) ∧ 4-method surface (`setArchived, getInfo, getActionsInfo, validate`). People variant additionally requires `replied, accepted, pendingReview`.

### Decisive source
```js
function isICampaign(value) {
    const arg = value;
    return ((0, guards_1.isIDBItem)(arg) &&
        arg.type === enums_1.CampaignType.People &&                       // positive enum discriminator
        (0, objects_1.objectHasProperties)(value, [...commonCampaignProperties, 'replied', 'accepted', 'pendingReview']) &&
        (0, objects_1.objectHasMethods)(value, [...commonCampaignMethods]));
}
function isIOrganizationsCampaign(value) {
    const arg = value;
    return ((0, guards_1.isIDBItem)(value) &&
        arg.type === enums_1.CampaignType.Organizations &&
        (0, objects_1.objectHasProperties)(value, [...commonCampaignProperties]) &&
        (0, objects_1.objectHasMethods)(value, [...commonCampaignMethods]) &&
        (0, objects_1.objectHasNoProperties)(value, ['replied', 'accepted', 'pendingReview']));   // absence REQUIRED
}
// enums.js: CampaignType People=1 | Organizations=2; CampaignSubListTypes Target=0..PendingReview=11
```

**Flow:** dbItem root check -> `type` enum discriminator picks the family -> shared whitelist ∧ method surface -> People adds three engagement counters; Organizations instead requires those same three keys to be ABSENT (`objectHasNoProperties` = `props.every(p => !(p in obj))`, key-presence via `in`).
**Invariant:** the org variant must not merely omit but demonstrably lack the people-only engagement fields — a people-shaped object fails `isIOrganizationsCampaign` even though it has every common property. The queued/processed/inProgress/successful/failed/excluded/skipped/exclude/replied/accepted/pendingReview property names mirror `CampaignSubListTypes` 1:1 (the UI sub-list taxonomy IS the field list); run-state lives in `state` against `CampaignStates` (active|completed|coolDown|nonWorkingHours|dailyLimitReached|archived|standBy).
**Probe:** deterministic node-require (no test runner exists in this ingest):
```bash
node -e "const g=require('/mnt/hdd/utopia/inspo/lh-basis/core/public-methods/models/campaigns/guards.js');const base={id:1,type:1,name:'c',actions:[],workQueue:[],createdAt:new Date(),target:{},queued:{},processed:{},inProgress:{},successful:{},failed:{},excluded:{},skipped:{},exclude:{},description:'',isPaused:false,isReadonly:false,isHidden:false,isStandByModeActive:false,isValid:true,state:0,excludeList:[],replied:{},accepted:{},pendingReview:{},setArchived(){},getInfo(){},getActionsInfo(){},validate(){}};console.log(g.isICampaign(base), g.isIOrganizationsCampaign(base));const org={...base,type:2};delete org.replied;delete org.accepted;delete org.pendingReview;console.log(g.isICampaign(org), g.isIOrganizationsCampaign(org))"
```
→ expect `true false false true` (people object passes only its own guard; org-stripped object passes only the org guard).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "campaign guards", file_pattern: "*campaigns*", limit: 10 });
```
Observed pass 3: ranks `isICampaign` / `isIOrganizationsCampaign` first (guards.js 35–41 / 42–49).

## Verdict
Adopt the split: ONE property/method core + per-family presence or absence sets, discriminated by an explicit enum field. Adapt the enum values and counter names to your host schema; keep the absence check as a hard gate (deleting the field from a fixture is how you test it). Omit product specifics (workQueue/excludeList semantics live in the unindexed engine). Caveats: property checks are key-presence minimums (extra keys pass); `type` is checked but not itself validated as ∈ CampaignType for the org guard beyond equality with the two constants.
