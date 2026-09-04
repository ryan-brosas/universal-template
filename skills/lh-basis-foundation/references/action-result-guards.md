<!-- capsule-v2 -->
# Action result guards — Why can the org variant's absence set be completely different from the entity-level one?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** when a result row records "what an action did to one target", which keys distinguish the People record from the Organizations record — and what does the org guard actually forbid?

## Shared outcome core + asymmetric family keys
**Path/Symbol:** `core/public-methods/models/actions/ActionResult/guards.js` — `commonProperties` (9–17), `isIActionResult` (18–20), `isIOrganizationsActionResult` (21–25).
**Signature:** `isIActionResult(data): boolean`; `isIOrganizationsActionResult(data): boolean`.
**Data Shape:** dbItem (`id>0`) ∧ 7 common properties (`actionVersionId, actionIterationId, liAccountId, result, createdAt, flags, targetPlatform`), where `result` is an `ActionResultStatus` code — a SIGNED value domain, see section below. People adds `personId, messages`; Organizations adds `organizationId` and forbids `invitedPlatform, messagedPlatform`.

### Decisive source
```js
function isIActionResult(data) {
    return (0, guards_1.isIDBItem)(data) && (0, objects_1.objectHasProperties)(data, [...commonProperties, 'personId', 'messages']);
}
function isIOrganizationsActionResult(data) {
    return ((0, guards_1.isIDBItem)(data) &&
        (0, objects_1.objectHasProperties)(data, [...commonProperties, 'organizationId']) &&
        (0, objects_1.objectHasNoProperties)(data, ['invitedPlatform', 'messagedPlatform']));
}
```

**Flow:** every result pins WHICH action version + iteration + LinkedIn account produced it (`actionVersionId/actionIterationId/liAccountId`), WHAT happened (`result`, `flags`, `targetPlatform`, `createdAt`). Family: people results carry the target person and the message trail (`personId`, `messages`); org results carry `organizationId`.
**Invariant — the trap:** the org guard's absence set is NOT the people-only presence set. It forbids `invitedPlatform`/`messagedPlatform` (per-surface platform-history props that only person flows write); it does NOT forbid `personId` or `messages`. A porter who copies the action-guard pattern and bans `personId`/`messages` on org results will reject valid rows — each family's absence list must be read from ITS OWN guard.
**Probe:** deterministic node-require:
```bash
node -e "const g=require('$REFERENCE_ROOT/lh-basis/core/public-methods/models/actions/ActionResult/guards.js');const core=['actionVersionId','actionIterationId','liAccountId','result','createdAt','flags','targetPlatform'].reduce((o,k)=>(o[k]=1,o),{id:3});const pr={...core,personId:11,messages:[]};const or_={...core,organizationId:5};const bad={...or_,invitedPlatform:'linkedin'};console.log(g.isIActionResult(pr),g.isIOrganizationsActionResult(pr),g.isIOrganizationsActionResult(or_),g.isIOrganizationsActionResult(bad))"
```
→ expect `true false true false` (org result with organizationId passes; adding invitedPlatform breaks it; people-shaped object fails the org guard via missing organizationId).

## The signed value domain of `result`
**Path/Symbol:** `core/public-methods/models/actions/ActionResult/enums.js` — `ActionResultStatus` (6–14).
**Signature:** reverse-keyed TS enum: `Skipped=-3, Excluded=-2, Failed=-1, Successful=1, Replied=2, PendingReview=3`.
**Data Shape:** six statuses on a signed axis with **no zero**.

### Decisive source
```js
ActionResultStatus[ActionResultStatus["Skipped"] = -3] = "Skipped";
ActionResultStatus[ActionResultStatus["Excluded"] = -2] = "Excluded";
ActionResultStatus[ActionResultStatus["Failed"] = -1] = "Failed";
ActionResultStatus[ActionResultStatus["Successful"] = 1] = "Successful";
ActionResultStatus[ActionResultStatus["Replied"] = 2] = "Replied";
ActionResultStatus[ActionResultStatus["PendingReview"] = 3] = "PendingReview";
```

**Invariant:** sign carries semantics. Negatives are NON-OUTCOME dispositions (skipped / excluded / failed); positives are real outcomes; zero is not a status at all. Consequences a porter must honor: truthiness on raw codes never classifies anything (`Failed = -1` is truthy), and `result > 0` is the correct outcome filter. This repeats a kernel-wide convention — `ActionTargetState.Removed = -1` (source-scoped-domain-enums) uses negative-means-not-an-outcome too.

**Probe (executed pass 14):**
```bash
node -e "const E=require('$REFERENCE_ROOT/lh-basis/core/public-methods/models/actions/ActionResult/enums.js').ActionResultStatus;console.log(Object.values(E).filter(v=>typeof v==='number').sort((a,b)=>a-b).join(' '),E.Successful>0,E.Failed>0)"
```
→ observed `-3 -2 -1 1 2 3 true false` (numeric domain exact, no zero; sign filter separates outcomes from dispositions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "action result guard", file_pattern: "*ActionResult*", limit: 10 });
```
Observed pass 3: returns both guards at guards.js 18–20 / 21–25.

## Verdict
Adopt: result records reference their producing unit by id triple (version, iteration, account) instead of embedding action snapshots; platform history travels ONLY on person results. Adapt id field names to your host. Omit `flags` bit semantics (defined in the unindexed engine). Cross-reference: action-lifecycle-guards for the entity-level split; person-aggregate-guard for how `invitedPlatform`-style slots appear on the person side.
