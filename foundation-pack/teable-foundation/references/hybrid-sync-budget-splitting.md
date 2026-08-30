<!-- capsule-v2 -->
# Hybrid sync-budget splitting — how does one strategy serve low-latency reads AND protect the transaction from unbounded recompute work?

## splitStepsByPolicy: seedTableOnly walks levels under per-table/total dirty budgets; lock conflicts degrade the WHOLE stage to an outbox task returning partial changes
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/strategies/HybridWithOutboxStrategy.ts` (whole file 822L) — config type+defaults (:71–134: `syncPolicy 'none'|'seedTableOnly'|'threshold'`, perTable 2000, total 5000, levelCap 1, `dispatchMode 'push'|'external'|'hybrid'`, `dispatchDelayMs ≥50` commit-race note), `splitStepsByPolicy` (:652–749, seedTableOnly walk :669–703, threshold extension :705–748), lock-unavailable requeue paths (:226–261 pre-lock, :330–366 mid-stage with reason `dirty_target_lock_unavailable`), before-image carry into follow-ups via `buildBeforeImageRecordsFromStepChanges` + `mergeBeforeImageRecords` (:593–606). Tests: `HybridWithOutboxStrategy.spec.ts` (731L suite).
**Signature:** `(plan, prepared: PreparedDirtyState, config) => {syncSteps, asyncSteps, syncMaxLevel}`.

### Decisive source
```ts
let syncMaxLevel = -1; let cumulativeDirty = 0;
for (const level of seedLevels) {                       // ascending
  const levelTotal = Σ dirtyCountByTable[table]; const levelMax = max(...);
  cumulativeDirty += levelTotal;
  if (levelMax > config.syncMaxDirtyPerTable) break;    // one hot table kills the level
  if (cumulativeDirty > config.syncMaxTotalDirty) break;
  syncMaxLevel = level;                                 // else this level runs inline
}
const syncSteps = seedSteps.filter(s => s.level <= syncMaxLevel);
// mid-stage conflict:
if (!isComputedUpdateLockUnavailable(syncResult.error)) return err(syncResult.error);
const task = buildOutboxTaskInput({ plan: currentPlan, ..., syncMaxLevel: -1, ... });
await this.outbox.enqueueOrMerge(task, context);        // WHOLE stage requeued
return ok({ changesByStep: allSyncChangesByStep });     // partial success is a SUCCESS
```

**Flow:** prepare the dirty-state snapshot → split planned steps into sync (cheap prefix of dependency levels within budgets) vs async (rest) → execute sync inline with wait=false locks → any advisory-lock contention converts the ENTIRE remaining stage into one merged outbox task (worker will replan against committed data) while ALREADY-computed sync changes return normally → enqueue async remainder with run bookkeeping (runId/originRunIds/step offsets preserved across the boundary).
**Invariant:** FOUR porters' traps: (1) Budgets count DIRTY RECORDS from prepared.stats, not rows-written — a level is rejected if ANY table exceeds per-table OR cumulative exceeds total; both gates must exist (one hot table ≠ many cold tables). (2) Degradation returns `ok()` with the partial sync changes — callers must treat queued-vs-done identically or they'll double-report; erroring here would roll back the user's write over an internal scheduling hiccup. (3) Requeue uses `syncMaxLevel: -1` so the WORKER replans from scratch against post-commit state instead of replaying possibly-stale mid-tx splits. (4) Follow-up stages merge ORIGINAL mutation before-images with ones derived from this stage's own changes (:593–606) — conditional-rollup filters need the mutation-time values even three hops later.
**Probe:** HybridWithOutboxStrategy.spec.ts suite pins split/degrade behavior at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "HybridWithOutboxStrategy splitStepsByPolicy enqueueOrMerge syncMaxLevel", limit: 5 });
```
## Verdict
Adopt when derived work must straddle inline-and-queued: budget-gated level prefixes, wait-free locks, whole-stage degradation to the queue, partial-result-as-success.
