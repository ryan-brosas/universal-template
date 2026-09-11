<!-- capsule-v2 -->
# Sync vs concurrent render loops + suspension resume — how does the render loop yield, and how does it resume after suspending?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** Where exactly are the yield points, what replaces `shouldYield` in throttled mode, and which suspended states resume by replaying versus unwinding?

## Twin render roots with a suspended-reason switch
**Path/Symbol:** `packages/react-reconciler/src/ReactFiberWorkLoop.js` — `renderRootSync` :2623–2768, `workLoopSync` :2772–2777, `renderRootConcurrent` :2779–3053, `workLoopConcurrent` :3056–3070, `workLoopConcurrentByScheduler` :3073–3078.
**Signature:** `renderRootSync(root: FiberRoot, lanes: Lanes, shouldYieldForPrerendering: boolean): RootExitStatus`; `renderRootConcurrent(root: FiberRoot, lanes: Lanes): RootExitStatus`.
**Data Shape:** Module state `workInProgress` (next unit of work), `workInProgressRoot/RenderLanes`, `workInProgressSuspendedReason` (`NotSuspended`, `SuspendedOnError`, `SuspendedOnData`, `SuspendedOnAction`, `SuspendedOnImmediate`, `SuspendedOnInstance`, `SuspendedAndReadyToContinue`, `SuspendedOnInstanceAndReadyToContinue`, `SuspendedOnHydration`, `SuspendedOnDeprecatedThrowPromise`) + `workInProgressThrownValue`.

### Decisive source
```js
// :2772-2777 — sync loop: NO yield checks at all.
function workLoopSync() {
  while (workInProgress !== null) { performUnitOfWork(workInProgress); }
}
// :3007-3018 — the concurrent loop's three flavors:
if (__DEV__ && ReactSharedInternals.actQueue !== null) {
  // in a unit test environment, we can't trust the result of `shouldYield`,
  // because the host I/O is likely mocked.
  workLoopSync();
} else if (enableThrottledScheduling) {
  workLoopConcurrent(includesNonIdleWork(lanes));
} else {
  workLoopConcurrentByScheduler();   // while (workInProgress !== null && !shouldYield())
}
// :3063-3068 — throttled wall-clock variant (deliberate animation tradeoff)
const yieldAfter = now() + (nonIdle ? 25 : 5);
do { performUnitOfWork(workInProgress); } while (workInProgress !== null && now() < yieldAfter);
// :2859-2875 — data suspension arms a ping INSIDE the loop, then exits:
const onResolution = () => {
  if ((reason === SuspendedOnData || reason === SuspendedOnAction) &&
      workInProgressRoot === root) {
    workInProgressSuspendedReason = SuspendedAndReadyToContinue;
  }
  ensureRootIsScheduled(root);
};
thenable.then(onResolution, onResolution);
break outer;   // exit render; RootInProgress returned → task yields
// :2846-2851 — on re-entry, resolved thenables REPLAY the unit instead of unwinding:
if (isThenableResolved(thenable)) { replaySuspendedUnitOfWork(unitOfWork); break; }
```

**Flow:** both loops share "if root/lanes changed since last time, throw away the stack (`prepareFreshStack`), else continue where left off" (:2635/:2787). Sync loop never yields; on re-entry after a mid-render suspend it immediately unwinds via `throwAndUnwindWorkLoop` (:2664–2724). Concurrent loop consults its pluggable yield check each unit; when suspended it either replays (resolved data / preloaded instance — resuming WITHOUT replay for completed host fibers :2909–2950), unwinds to a fallback/error boundary, or exits with `RootInProgress` to wait for a ping that calls `ensureRootIsScheduled`.
**Invariant:** Yield points sit BETWEEN units of work only — a fiber is never torn mid-render. Suspension always leaves through the same outer-loop boundary so the stack can be resumed or discarded coherently. In act scopes the yield check is bypassed entirely because mocked I/O makes it untrustworthy.
**Probe:** `packages/react-reconciler/src/__tests__/ReactUpdatePriority-test.js` :109–155 — transition renders `'A2'` then is interrupted by a continuous update before finishing: observable evidence that the concurrent loop stops between units and re-renders under new lanes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "renderRootConcurrent suspended reason replaySuspendedUnitOfWork shouldYield workLoopConcurrent", limit: 10 });
// Observed: renderRootSync :2623-2768 exact; workLoopConcurrent/
// workLoopConcurrentByScheduler resolve inside ReactFiberWorkLoop.js line fields.
```

## Verdict
Adopt the twin-loop split (sync = zero checks; concurrent = per-unit yield), the prepareFreshStack-on-lane-change resume rule, and the suspended-reason switch distinguishing REPLAY (data resolved) from UNWIND (fallback needed). Adapt the yield source: wall-clock budget (25ms non-idle / 5ms idle) if you lack a scheduler-consulting `shouldYield`. Omit hydration/deprecated-throw-promise reasons unless porting those planes. Coverage caveat: file parse_partial (flagged lines ≤565 only); all cited ranges read directly.
