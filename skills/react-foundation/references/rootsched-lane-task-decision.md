<!-- capsule-v2 -->
# Per-root task decision tree — when does a root get a Scheduler callback, and when does sync work get none at all?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** Given computed next lanes for a root, what are ALL the outcomes, and why do synchronous lanes never produce a Scheduler task?

## Three-outcome scheduling decision
**Path/Symbol:** `packages/react-reconciler/src/ReactFiberRootScheduler.js:384-509` (`scheduleTaskForRootDuringMicrotask`).
**Signature:** `scheduleTaskForRootDuringMicrotask(root: FiberRoot, currentTime: number): Lane`.
**Data Shape:** Reads `root.pendingLanes/suspendedLanes/pingedLanes/warmLanes`, `root.callbackNode` (opaque Scheduler task handle), `root.callbackPriority` (a **Lane**, not a scheduler priority). Returns the lane representing the scheduled priority, or NoLane when nothing is scheduled.

### Decisive source
```js
// :442-456 — the surprising outcome: sync lanes schedule NOTHING.
if (
  includesSyncLane(nextLanes) &&
  !checkIfRootIsPrerendering(root, nextLanes)
) {
  // Synchronous work is always flushed at the end of the microtask, so we
  // don't need to schedule an additional task.
  if (existingCallbackNode !== null) { cancelCallback(existingCallbackNode); }
  root.callbackPriority = SyncLane;
  root.callbackNode = null;
  return SyncLane;
}
// :462-474 — dedupe by highest-priority lane equality
if (newCallbackPriority === existingCallbackPriority && !(...act...)) {
  return newCallbackPriority;   // reuse existing task
} else {
  cancelCallback(existingCallbackNode);  // priority changed → cancel + re-post
}
// :481-503 — lanes → Scheduler level; Immediate deliberately unused now
switch (lanesToEventPriority(nextLanes)) {
  case DiscreteEventPriority:
  case ContinuousEventPriority:
    schedulerPriorityLevel = UserBlockingSchedulerPriority; break;
  case DefaultEventPriority: schedulerPriorityLevel = NormalSchedulerPriority; break;
  case IdleEventPriority:    schedulerPriorityLevel = IdleSchedulerPriority; break;
  default:                   schedulerPriorityLevel = NormalSchedulerPriority;
}
const newCallbackNode = scheduleCallback(schedulerPriorityLevel,
  performWorkOnRootViaSchedulerTask.bind(null, root));
```

**Flow:** `markStarvedLanesAsExpired(root, currentTime)` first (:397) → compute `nextLanes` via `getNextLanes` (or `pendingPassiveEffectsLanes` under `enableYieldingBeforePassive`) → **outcome A** nothing-to-do (NoLanes / suspended-on-data mid-render / pending commit): cancel stale node, `callbackNode=null, callbackPriority=NoLane`, return NoLane → **outcome B** sync lanes & not prerendering: cancel node, mark priority=SyncLane with a NULL node (flushed by the same microtask's tail call to `flushSyncWorkAcrossRoots_impl`) → **outcome C** concurrent: reuse-or-cancel by `getHighestPriorityLane(nextLanes) === callbackPriority`, map lanes→scheduler level, post `performWorkOnRootViaSchedulerTask.bind(null, root)`.
**Invariant:** At most one outstanding callback per root; `callbackPriority` is compared as a whole lane value, so any priority change cancels and re-schedules rather than stacking tasks. Prerendering roots use the concurrent loop even for sync lanes so they never block the main thread.
**Probe:** `packages/react-reconciler/src/__tests__/ReactUpdatePriority-test.js` :109–155 — a continuous-priority update issued mid-transition interrupts and re-renders `(hidden)` before the transition resumes: evidence that a higher-priority lane changes `newCallbackPriority` and forces re-scheduling.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "scheduleTaskForRootDuringMicrotask callbackPriority cancelCallback lanesToEventPriority", limit: 10 });
// Observed: top hits in ReactFiberRootScheduler.js — scheduleImmediateRootScheduleTask
// :650-696, scheduleTaskForRootDuringMicrotask :384-509, ensureRootIsScheduled :116-152.
```

## Verdict
Adopt the three-outcome tree and especially outcome B: representing "sync flush pending" as `callbackPriority=SyncLane` + null node, letting the microtask tail do the render — this is what makes Scheduler Immediate priority unnecessary in modern React (see the :482–484 comment). Adapt the lane→scheduler-level switch to your own scale. Omit act-queue fakes (`fakeActCallbackNode`) outside test harnesses. Coverage caveat: file parse_partial (scattered lines); cited ranges read directly.
