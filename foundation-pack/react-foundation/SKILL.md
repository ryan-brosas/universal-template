---
name: react-foundation
description: "Use when porting cooperative time-slicing schedulers, priority-ordered task queues, delayed-task timers, macrotask yield/error-resume loops, or lane/priority-bitmap scheduling kernels modeled on React's Scheduler (`packages/scheduler`) and the react-reconciler root-scheduling plane (`ReactFiberRootScheduler`, `ReactFiberWorkLoop` render entry, `ReactFiberLane`). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
disable-model-invocation: true
---
# React: Fiber scheduler foundation

## Use this for
Use when porting cooperative time-slicing schedulers, priority-ordered task queues, delayed-task timers, macrotask yield/error-resume loops, or lane/priority-bitmap scheduling kernels modeled on React's Scheduler (`packages/scheduler`) and the react-reconciler root-scheduling plane (`ReactFiberRootScheduler`, `ReactFiberWorkLoop` render entry, `ReactFiberLane`). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/scheduler-minheap-id-tiebreak.md` — How do two equal-priority tasks keep FIFO order through a binary heap that only compares numbers?
- `references/scheduler-two-queue-delay-ladder.md` — How do delayed tasks wait without blocking ready work, and when exactly does a host timeout get armed?
- `references/scheduler-priority-expiration-table.md` — What timeout does each priority level get, and how does expiration override the frame-yield check?
- `references/scheduler-continuation-yield-contract.md` — When a task returns a continuation, why must the loop yield immediately even with budget left?
- `references/scheduler-error-resume-macrotask.md` — How does the queue survive a throwing task without a try/catch around user code?
- `references/scheduler-host-transport-selection.md` — Which host API posts the next work tick, and why is it not always MessageChannel?
- `references/scheduler-root-task-dedup-boundary.md` — How does a consumer map its own priorities onto the scheduler and keep one task per root?
- `references/rootsched-microtask-gate.md` — When an update hits a root, what runs immediately versus later, and where is it safe to mutate the root schedule list?
- `references/rootsched-sync-drain-loop.md` — When flushSync fires, how does sync work finish across all roots, past roots that throw?
- `references/rootsched-lane-task-decision.md` — Given computed next lanes for a root, what are all outcomes, and why do sync lanes never produce a Scheduler task?
- `references/rootsched-concurrent-entry-continuation.md` — After the work loop yields, what decides whether a Scheduler task continues versus dies, and why is didTimeout only defensive?
- `references/workloop-timeslice-decision.md` — At render time, what forces the synchronous loop despite async updates, and how are errored/fatal renders retried?
- `references/workloop-sync-vs-concurrent-loops.md` — Where are the yield points, what replaces shouldYield in throttled mode, and which suspensions replay versus unwind?
- `references/lane-bitmap-total-order.md` — How does a bitmask encode priority with pure integer ops, and when may an in-progress render be interrupted?

## Capsule map
### Scheduler kernel (packages/scheduler)
- **Heap ordering** — `scheduler-minheap-id-tiebreak`: min-heap on `sortIndex` then insertion `id`; cancellation is lazy `callback = null`.
- **Delayed tasks** — `scheduler-two-queue-delay-ladder`: timerQueue by startTime, taskQueue by expirationTime; fired timers re-sort via `timer.sortIndex = timer.expirationTime`; at most one armed host timeout.
- **Priorities & expiration** — `scheduler-priority-expiration-table`: Immediate −1 / UserBlocking 250 / Normal 5000 / Low 10000 / Idle 2³⁰−1; expired tasks never yield.
- **Continuations** — `scheduler-continuation-yield-contract`: `Callback = boolean => ?Callback`; returning a function forces a fresh macrotask regardless of remaining slice.
- **Error resume** — `scheduler-error-resume-macrotask`: `hasMoreWork = true` sentinel + finally re-post; no catch in prod path; flushWork restores priority/reentrancy state.
- **Host transport** — `scheduler-host-transport-selection`: setImmediate > MessageChannel > setTimeout ladder; single-flight `isMessageLoopRunning`.
### Reconciler root-scheduling plane
- **Consumer boundary** — `scheduler-root-task-dedup-boundary`: lanes→scheduler-priority switch, one callbackNode/callbackPriority per root, act-queue bypass.
- **Microtask gate** — `rootsched-microtask-gate`: intrusive root linked list appended anywhere but unlinked ONLY inside the coalesced microtask; single-flight latches incl. DEV act twin; `mightHavePendingSyncWork` tri-state flag.
- **Sync drain** — `rootsched-sync-drain-loop`: flushSync is a do-while fixpoint across ALL roots guarded by reentrancy latch + fast-exit flag; passive-effect flush bails to the outer loop to recompute priority.
- **Task decision** — `rootsched-lane-task-decision`: three outcomes — cancel+null (suspended/pending commit), SyncLane priority with NULL node (sync flushed at microtask tail), or reuse/cancel by highest-lane equality then Scheduler callback.
- **Concurrent entry** — `rootsched-concurrent-entry-continuation`: three defensive exits before rendering; continuation iff `root.callbackNode === originalCallbackNode` after re-running the decision at end-of-task; `didTimeout` kept only for an unfixed Scheduler bug.
- **Time-slice gate** — `workloop-timeslice-decision`: forceSync ∨ blocking lanes ∨ expired lanes → sync loop; prerendering overrides toward concurrent; tear-detected renders redo synchronously; RootErrored retries sync then commits anyway.
- **Render loops** — `workloop-sync-vs-concurrent-loops`: sync loop has zero yield checks; concurrent loop yields per-unit via shouldYield or 25/5ms wall clock (throttled); act scopes force sync because mocked I/O breaks shouldYield; suspension resumes by replay (resolved data) or unwind (fallback).
- **Lane algebra** — `lane-bitmap-total-order`: bit position IS priority; `lanes & -lanes`, right-fill clz32 masks, numeric interrupt rule `nextLane >= wipLane` with Default-doesn't-interrupt-Transitions carve-out; retry lanes excluded from expiry.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
facebook/react (MIT), `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory project `react` (full mode, generation 2026-08-25T20:08:45Z, 50867 nodes / 184170 edges). Coverage caveats: 860 parse_partial files incl. every decisive scheduler path (`forks/Scheduler.js` flagged 1–614 whole-file) AND every pass-2 path (`ReactFiberLane.js` flagged 1–1309 whole-file; `ReactFiberRootScheduler.js`/`ReactFiberWorkLoop.js` scattered) — all cited ranges were read directly from source; 0 skipped files.

## Full view (memory graph)
Revalidate `react` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Graph note: symbol extraction inside `packages/scheduler/src/forks/Scheduler.js` is partial (parse_partial) — navigate by file+line from this leaf's citations, then read source directly. Same applies to `ReactFiberLane.js`. Graph naming note at this pin: the concurrent entry symbol is `performWorkOnRootViaSchedulerTask` (ReactFiberRootScheduler.js :513–606); older `performConcurrentWorkOnRoot` names do not exist in the graph.

## Boundaries
Adopt the pure scheduling contracts above (heap ordering, delay ladder, continuation protocol, error-resume loop, microtask gate, lane bitmap algebra); adapt the host transport selection, feature-flag constants, and wall-clock yield budgets to your environment; omit React-specific consumers you don't carry (reconciler commit phases, hydration suspended reasons, View Transition indicators), profiling instrumentation, and the deprecated postTask fork unless porting those planes deliberately.
