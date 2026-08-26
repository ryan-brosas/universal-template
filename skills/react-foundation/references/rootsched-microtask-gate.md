<!-- capsule-v2 -->
# Root-schedule microtask gate — when does React actually decide what work to schedule?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** When an update hits a root, what runs immediately versus later, and where is it safe to mutate the root schedule list?

## Intrusive root list + single-flight microtask
**Path/Symbol:** `packages/react-reconciler/src/ReactFiberRootScheduler.js` (`firstScheduledRoot`, `ensureRootIsScheduled`, `ensureScheduleIsScheduled`, `processRootScheduleInMicrotask`) (:96–169, :259–348).
**Signature:** `ensureRootIsScheduled(root: FiberRoot): void`; `processRootScheduleInMicrotask(): void`.
**Data Shape:** Roots form an intrusive singly-linked list (`root.next`) from `firstScheduledRoot` to `lastScheduledRoot`. Module flags: `didScheduleMicrotask` (prod dedupe), `didScheduleMicrotask_act` (DEV-only twin for non-awaited `act` queues), `mightHavePendingSyncWork`, `isFlushingWork`.

### Decisive source
```js
// :125-134 — append is idempotent and cheap; it does NOT compute priorities.
if (root === lastScheduledRoot || root.next !== null) {
  // Fast path. This root is already scheduled.
} else { /* ...link at tail... */ }
mightHavePendingSyncWork = true;
ensureScheduleIsScheduled();

// :294-298 — removal discipline
if (nextLanes === NoLane) {
  // This root has no more pending work. Remove it from the schedule. To
  // guard against subtle reentrancy bugs, this microtask is the only place
  // we do this — you can add roots to the schedule whenever, but you can
  // only remove them here.
```

**Flow:** update → `ensureRootIsScheduled`: (1) link root into list if absent (O(1) fast path if already linked), (2) set `mightHavePendingSyncWork=true`, (3) `ensureScheduleIsScheduled` posts **one** microtask (`didScheduleMicrotask` latch). Later, `processRootScheduleInMicrotask` clears both latches FIRST (:262–265 — so work done inside can re-arm), resets `mightHavePendingSyncWork=false`, walks every root calling `scheduleTaskForRootDuringMicrotask`, unlinks drained roots, re-raises `mightHavePendingSyncWork` per-root still holding sync lanes (:320–329), then flushes sync work at the end of the same microtask.
**Invariant:** The latch must be cleared before any scheduling decision runs, or updates fired during the microtask would be lost until some later event; roots may be appended anywhere but unlinked only inside this microtask.
**Probe:** `packages/react-reconciler/src/__tests__/ReactFlushSync-test.js` `'completely exhausts synchronous work queue even if something throws'` (:294–344) — three roots updated in one event all drain through one schedule pass even when earlier roots throw.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "ensureRootIsScheduled processRootScheduleInMicrotask microtask schedule immediate root lanes", limit: 10 });
// Observed @ gen 2026-08-25T20:08:45Z: processRootScheduleInMicrotask :259-348 top rank,
// then scheduleImmediateRootScheduleTask :650-696, scheduleTaskForRootDuringMicrotask
// :384-509, ensureRootIsScheduled :116-152 — all in-file, exact line match.
```

## Verdict
Adopt the two-phase shape: O(1) append + flag-set on update, full priority computation deferred to one coalesced microtask that clears its own latch first and is the only place allowed to unlink roots. Adapt the act-queue DEV twin (`didScheduleMicrotask_act`) only if you support non-awaited test scopes. Omit the transition-indicator plumbing in the same microtask (`startDefaultTransitionIndicatorIfNeeded`) unless porting View Transitions. Coverage caveat: file is parse_partial (scattered lines); every cited range was read directly from source.
