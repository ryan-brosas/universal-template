<!-- capsule-v2 -->
# Action-version stats projection — How do you report queue-operation outcomes when the same person can be both successfully processed AND excluded?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** how are raw Set-based operation stats folded into displayable counts without double-reporting excluded people as successes?

## Set-fold projection with NET-of-exclusions reclassification
**Path/Symbol:** `core/public-methods/shared-types/actionVersion/types.js` — `ICreateActionVersionStats.convertOperationStatsToActionVersionStats` (8–54); companion guard `core/public-methods/shared-types/actionVersion/guards.js:isIAdditionalAddToTargetParams` (7–12).
**Signature:** `convertOperationStatsToActionVersionStats(operationsStats): { total: {...} }`; `isIAdditionalAddToTargetParams(data): boolean`.
**Data Shape:** input = up to six OPTIONAL operation slots (`target`, `addToTarget`, `removeFromTarget`, `addToQueue`, `removeFromQueue`) plus two exclude-list carriers (`excludeByActionExcludeList`, `excludeByCampaignExcludeList`); every populated slot holds **Sets of person ids** (`.size`, never `.length`). Output = `{ total: { target?, addToTarget?, removeFromTarget?, addToQueue?, removeFromQueue? } }` with plain-number counts.

### Decisive source
```js
if (addToQueue) {
    const excludeList = new Set([
        ...(excludeByCampaignExcludeList?.successful.values() || []),
        ...(excludeByActionExcludeList?.successful.values() || []),
    ]);
    const successful = [...addToQueue.successful.values()]
        .filter((personId) => !excludeList.has(personId)).length;
    const inExcludeList = [...addToQueue.successful.values()]
        .filter((personId) => excludeList.has(personId)).length;
    stats.total.addToQueue = { successful, inExcludeList, alreadyInQueue: addToQueue.alreadyInQueue.size };
}
```

**Flow:** start `{total:{}}` -> per-slot if-truthy fold (absent slot simply absent from output, no zero-filling) -> each slot projects its Sets to counts via `.size` -> EXCEPT `addToQueue`: union the campaign- and action-level exclude-list successful Sets, then SPLIT `addToQueue.successful` into `successful` (not in either exclude list) and `inExcludeList` (reclassified out of success).
**Invariant:** a person can appear in `addToQueue.successful` AND in an exclude list's successful set; the projection must report them once, under `inExcludeList` — naive `.size` reporting would double-count. Optional-slot folding means consumers must treat every key of `total` as possibly absent; the companion guard requires BOTH copy-source DBIds present (`copyCollectingScopeAndPlatformsFromActionId`, `copyPrevActionTargetPlatformFromActionId`) — copy-from-action parameters have no nullable slot.
**Probe:** `node -e`: ops fixture with `addToQueue.successful = new Set([1,2,3])` and `excludeByActionExcludeList.successful = new Set([2])` → `stats.total.addToQueue.successful === 2 && inExcludeList === 1 && alreadyInQueue === 0`; omit all slots → deep-equal `{total:{}}`; `target.added.length` instead of Set → TypeError (Sets required). Guard: missing either copy-source id → `false`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.shared-types.actionVersion.types.convertOperationStatsToActionVersionStats" });
```

## Verdict
Adopt the net-of-exclusions split whenever one operation's output can be post-filtered by another subsystem's exclusion result — count, then reclassify, never subtract after the fact. Adapt slot names to your operation vocabulary. Omit LinkedIn action semantics. Coverage: no_recorded_issue ×2 @ gen 2026-08-23T00:11:49Z; probe executed against shipped dist module (no test runner in ingest — standing block).
