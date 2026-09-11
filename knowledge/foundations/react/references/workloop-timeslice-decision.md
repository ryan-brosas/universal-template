<!-- capsule-v2 -->
# Time-slice gate + render exit-status machine — when does a root render synchronously even though its update was async?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** At the moment of rendering, what forces the synchronous loop despite concurrent lanes, and how are errored/suspended renders retried?

## shouldTimeSlice gate and the do-while exit machine
**Path/Symbol:** `packages/react-reconciler/src/ReactFiberWorkLoop.js:1137-1325` (`performWorkOnRoot`), with `recoverFromConcurrentError` :1327+.
**Signature:** `performWorkOnRoot(root: FiberRoot, lanes: Lanes, forceSync: boolean): void`.
**Data Shape:** Entry guard `(executionContext & (RenderContext | CommitContext)) !== NoContext` → throw `'Should not already be working.'`. Produces a `RootExitStatus` (`RootInProgress` / `RootErrored` / `RootFatalErrored` / shell-suspended variants) consumed by an unbounded `do {} while (true)`.

### Decisive source
```js
// :1165-1181 — the gate. Expired work and blocking lanes downgrade to sync.
const shouldTimeSlice =
  (!forceSync &&
    !includesBlockingLane(lanes) &&
    !includesExpiredLane(root, lanes)) ||
  // If we're prerendering, then we should use the concurrent work loop
  // even if the lanes are synchronous, so that prerendering never blocks
  // the main thread.
  checkIfRootIsPrerendering(root, lanes);

let exitStatus = shouldTimeSlice
  ? renderRootConcurrent(root, lanes)
  : renderRootSync(root, lanes, true);
// :1223-1244 — interleaved-mutation defense: redo the render SYNC.
if (renderWasConcurrent && !isRenderConsistentWithExternalStores(finishedWork)) {
  // A store was mutated in an interleaved event. Render again,
  // synchronously, to block further mutations.
  exitStatus = renderRootSync(root, lanes, false);
  renderWasConcurrent = false;
  continue;
}
// :1246-1291 — RootErrored → retry synchronously on remaining lanes; if it
// errors AGAIN, proceed to commit anyway (:1284-1289).
// :1292-1308 — RootFatalErrored → prepareFreshStack + markRootSuspended(
//   didAttemptEntireTree = true) "to avoid scheduling a prerender"; break.
finishConcurrentRender(root, exitStatus, finishedWork, lanes, renderEndTime);
// ...
ensureRootIsScheduled(root);   // :1324 — ALWAYS re-arm scheduling at exit
```

**Flow:** compute `shouldTimeSlice` → render once (sync or concurrent) → loop: `RootInProgress` = still rendering, break out and yield to caller (task continues per rootsched-concurrent-entry-continuation) → completed renders check external-store consistency (concurrent tear detector), then error ladder, then `finishConcurrentRender` for commit → every path ends with `ensureRootIsScheduled(root)` so leftover lanes re-enter the microtask gate.
**Invariant:** `forceSync`, blocking lanes (sync/continuous/default/gesture groups), and expired lanes all bypass time-slicing; prerendering overrides them in the opposite direction. A torn concurrent render is never committed — it is redone synchronously. Fatal errors mark the whole tree attempted to suppress speculative prerenders.
**Probe:** `packages/react-reconciler/src/__tests__/ReactUpdatePriority-test.js` :38–57 — passive-effect `setState` triggered by a flushSync'd render commits at default priority afterward (`assertLog([1])` inside act, `[2]` after): evidence that lane priority of follow-up work is recomputed at re-scheduling time, not inherited from the forcing flush.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "shouldTimeSlice includesBlockingLane includesExpiredLane performWorkOnRoot", limit: 10 });
// Observed: getWorkInProgressRootRenderLanes :776-778 nearby; renderRootSync
// :2623-2768 and performWorkOnRoot :1137-1325 resolve with exact line fields.
```

## Verdict
Adopt the three-way downgrade rule (forceSync / blocking-lane bitmap test / expired-lane test) plus the prerendering override, the tear-detection re-render, and "always ensureRootIsScheduled on exit". Adapt `includesBlockingLane`'s exact lane set to your priority model. Omit the profiler/performance-track yield timers unless you port instrumentation. Coverage caveat: ReactFiberWorkLoop.js parse_partial (flagged lines ≤565 only); cited ranges read directly.
