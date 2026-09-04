<!-- capsule-v2 -->
# flushSync multi-root drain loop — how does sync work finish across all roots, past throwing roots?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** When flushSync fires, how does React guarantee every root's sync lanes render in one pass — including roots updated mid-drain and roots that throw?

## Fixpoint drain across the root list
**Path/Symbol:** `packages/react-reconciler/src/ReactFiberRootScheduler.js` (`flushSyncWorkOnAllRoots`, `flushSyncWorkAcrossRoots_impl`, `performSyncWorkOnRoot`) (:171–247, :608–622).
**Signature:** `flushSyncWorkAcrossRoots_impl(syncTransitionLanes: Lanes | Lane, onlyLegacy: boolean)`; `performSyncWorkOnRoot(root: FiberRoot, lanes: Lanes)`.
**Data Shape:** Inputs: extra lanes to force sync (popstate eager transitions), legacy-only flag. Reads module flags `isFlushingWork` (reentrancy), `mightHavePendingSyncWork` (fast exit). Per root consults `root.pendingLanes` via `getNextLanes` / `getNextLanesToFlushSync`.

### Decisive source
```js
// :189-199
if (isFlushingWork) { return; }          // Prevent reentrancy.
if (!mightHavePendingSyncWork) { return; } // Fast path. There's no sync work to do.
// :204-245
isFlushingWork = true;
do {
  didPerformSomeWork = false;
  let root = firstScheduledRoot;
  while (root !== null) {
    /* ...getNextLanes(root, ...) → if includesSyncLane(nextLanes) &&
       !checkIfRootIsPrerendering(root, nextLanes):
       didPerformSomeWork = true; performSyncWorkOnRoot(root, nextLanes); */
    root = root.next;
  }
} while (didPerformSomeWork);  // fixpoint: work scheduled mid-drain gets a pass
isFlushingWork = false;
```

**Flow:** caller checks execution context → reentrancy guard → fast-exit flag → repeat {walk all roots; for each with unblocked sync lanes call `performSyncWorkOnRoot`} until a full pass performs no work. `performSyncWorkOnRoot` first calls `flushPendingEffects()`; if effects were flushed it **returns null without rendering** so the outer fixpoint recomputes priority (:611–616). The popstate variant uses `getNextLanesToFlushSync(root, syncTransitionLanes)` which unions `SyncUpdateLanes | extraLanes` and right-fill masks equal-or-higher-priority pending lanes, always OR-ing in SyncLane as the batch priority marker (ReactFiberLane.js :363–409).
**Invariant:** A throwing root must not starve later roots in the same flush (each root's error is caught by the reconciler's error machinery and recorded); the loop terminates only when an entire pass performs zero work — a single `while` pass is insufficient because renders can schedule more sync work.
**Probe:** `packages/react-reconciler/src/__tests__/ReactFlushSync-test.js` :294–344 — root1/root2 render throwing components, root3 still logs `'aww'`; errors surface as one `AggregateError(errors.length === 2)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "flushSync work across roots performSyncWorkOnRoot", limit: 10 });
// Observed: flushSyncWorkOnAllRoots :171-175, flushSyncWorkAcrossRoots_impl :185-247,
// performSyncWorkOnRoot :608-622 resolved in-project with exact line fields.
```

## Verdict
Adopt the do-while-until-fixpoint drain plus the two cheap guards (reentrancy latch, `mightHavePendingSyncWork` flag maintained by the microtask gate). Adopt "flush passive effects first, then bail to the outer loop" as the priority-recompute boundary. Adapt lane predicates (`includesSyncLane`, `checkIfRootIsPrerendering`) to your own priority model. Omit the legacy-only root filter unless you carry a legacy render mode. Coverage caveat: ReactFlushSync-test.js parse_partial at :41,:52 only — cited test range read directly.
