<!-- capsule-v2 -->
# Concurrent task entry + continuation identity — when does a Scheduler task for a root continue versus die?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** After the work loop yields, what decides whether the same Scheduler task keeps running, and why is `didTimeout` only defensive here?

## Task entry with three defensive exits, then continuation by node identity
**Path/Symbol:** `packages/react-reconciler/src/ReactFiberRootScheduler.js:511-606` (`RenderTaskFn`, `performWorkOnRootViaSchedulerTask`).
**Signature:** `(root: FiberRoot, didTimeout: boolean) => RenderTaskFn | null` where `type RenderTaskFn = (didTimeout: boolean) => RenderTaskFn | null`.
**Data Shape:** Captures `originalCallbackNode = root.callbackNode` on entry; returns a bound function of itself as the Scheduler continuation, or `null` to end the task.

### Decisive source
```js
// :530-541 — exit 1: an async commit (e.g. View Transition) owns the main thread
if (hasPendingCommitEffects()) {
  root.callbackNode = null;
  root.callbackPriority = NoLane;
  return null;   // rely on commit's ensureRootIsScheduled to re-post later
}
// :545-558 — exit 2: flushing passive effects may have canceled/replaced this task
const originalCallbackNode = root.callbackNode;
const didFlushPassiveEffects = flushPendingEffectsDelayed();
if (didFlushPassiveEffects && root.callbackNode !== originalCallbackNode) {
  return null;
}
// :585-590
// TODO: We only check `didTimeout` defensively, to account for a Scheduler
// bug we're still investigating. Once the bug in Scheduler is fixed,
// we can remove this, since we track expiration ourselves.
const forceSync = !disableSchedulerTimeoutInWorkLoop && didTimeout;
performWorkOnRoot(root, lanes, forceSync);
// :599-605 — "we cheat a bit": rerun the decision outside a microtask
scheduleTaskForRootDuringMicrotask(root, now());
if (root.callbackNode != null && root.callbackNode === originalCallbackNode) {
  return performWorkOnRootViaSchedulerTask.bind(null, root);  // continuation
}
return null;
```

**Flow:** Scheduler fires task → exit if pending commit effects → flush delayed passive effects and abort if our node was replaced (stale-task detection by reference identity) → recompute lanes via `getNextLanes` (must re-run: Scheduler may batch several callbacks into one browser macrotask without yielding to microtasks, so updates scheduled "during this task" are already visible — see TODO :561–579) → render (`forceSync` only from the defensive `didTimeout`) → re-run the per-root decision at end-of-task → continue iff the freshly scheduled callbackNode is still the SAME object that was executing.
**Invariant:** A task may only return its own bound self as continuation when the decision pass re-elected it; any cancel/re-schedule (priority change, suspension, drain) makes the old object stale and the task must die. This is the reconciler-side twin of Scheduler's `boolean => ?Callback` contract (see scheduler-continuation-yield-contract).
**Probe:** `packages/scheduler/src/__tests__/Scheduler-test.js` `'yielding continues in a new task regardless...'` (:320–351) pins the underlying Scheduler-side continuation behavior this function relies on; reconciler-side identity rule has no direct unit test (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "continuation callback yield workLoop hasMoreWork performWorkOnRootViaSchedulerTask", limit: 10 });
// Observed: performWorkOnRootViaSchedulerTask :513-606 and performWorkOnRoot
// :1137-1325 resolve in-project; scheduler yield-family hits appear alongside.
```

## Verdict
Adopt the identity-check continuation protocol and the three exits (commit-effects defer, passive-flush staleness, empty-lane recompute). Adopt `didTimeout` ONLY as a defensive force-sync flag — at this pin React tracks expiration in lane space (`markStarvedLanesAsExpired`), not Scheduler timeouts, so do not port it as a real timeout mechanism. Adapt the "rerun scheduling decision at end of browser task" cheat to whatever your scheduler guarantees about microtask draining between callbacks. Coverage caveat: file parse_partial (scattered lines); cited ranges read directly.
