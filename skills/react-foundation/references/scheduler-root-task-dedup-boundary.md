<!-- capsule-v2 -->
# Scheduler root-task dedup boundary — how does a consumer map its priorities onto the scheduler and keep one task per root?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** When many updates hit the same root at mixed priorities, how does react-reconciler avoid flooding Scheduler with tasks, and which scheduler levels does it actually use?

## One callbackNode/callbackPriority per root + lane→priority switch
**Path/Symbol:** `packages/react-reconciler/src/ReactFiberRootScheduler.js` scheduling tail (:441–508), act wrapper `scheduleCallback` (:624–639), Safari fallback (:663–688); twin wrapper in `packages/react-reconciler/src/ReactFiberWorkLoop.js:scheduleCallback` (:5584–5599).
**Signature:** `lanesToEventPriority(lanes: Lanes): EventPriority` (implemented at `packages/react-reconciler/src/ReactEventPriorities.js:55–67`) → switch to `UserBlockingSchedulerPriority | NormalSchedulerPriority | IdleSchedulerPriority`; `scheduleCallback(priorityLevel, performWorkOnRootViaSchedulerTask.bind(null, root))`.
**Data Shape:** Root carries `callbackNode: Task|null` and `callbackPriority: Lane`; sync-lane work bypasses Scheduler entirely (`root.callbackNode = null; root.callbackPriority = SyncLane`, :454–456).

### Decisive source
```js
// We use the highest priority lane to represent the priority of the callback.
const existingCallbackPriority = root.callbackPriority;
const newCallbackPriority = getHighestPriorityLane(nextLanes);

if (newCallbackPriority === existingCallbackPriority ...) {
  // The priority hasn't changed. We can reuse the existing task.
  return newCallbackPriority;
} else {
  // Cancel the existing callback. We'll schedule a new one below.
  cancelCallback(existingCallbackNode);
}

let schedulerPriorityLevel;
switch (lanesToEventPriority(nextLanes)) {
  // Scheduler does have an "ImmediatePriority", but now that we use
  // microtasks for sync work we no longer use that. ...
  case DiscreteEventPriority:
  case ContinuousEventPriority:
    schedulerPriorityLevel = UserBlockingSchedulerPriority;
    break;
  case DefaultEventPriority:
    schedulerPriorityLevel = NormalSchedulerPriority;
    break;
  case IdleEventPriority:
    schedulerPriorityLevel = IdleSchedulerPriority;
```

**Flow:** update → microtask re-evaluation (`scheduleTaskForRootDuringMicrotask`) → compute next lanes → same highest priority? keep existing task : cancel old task, schedule ONE new task bound to the root → task runs, recomputes lanes, and either returns a continuation (same callbackNode still owns work) or lets the root go idle.
**Invariant:** The scheduler sees at most one outstanding task per root; coalescing is by comparing the *highest* pending lane with the currently scheduled priority. ImmediatePriority is deliberately unused by this consumer (sync work flushes end-of-microtask); Discrete and Continuous event work both collapse to UserBlocking. Test-only `act` swaps Scheduler for an internal queue via a fake sentinel node (`fakeActCallbackNode`).

**Probe:** `packages/react-reconciler/src/__tests__/ReactSchedulerIntegration-test.js`: `'act` bypasses Scheduler methods completely' describe (:325–361) mocks `unstable_shouldYield` to always return true and asserts renders inside `act` still complete (guard throws 'Detected an infinite loop' otherwise) — pinning both the act-bypass wrapper and the fact that production scheduling depends on shouldYield honesty.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "ensureRootIsScheduled callbackPriority lanesToEventPriority scheduleCallback", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the dedup-by-priority-key pattern (cancel-and-reschedule on priority change, reuse otherwise) for any scheduler consumer. Adapt the lane→priority table to your own event taxonomy; note the deliberate non-use of Immediate. Omit React's act machinery. Coverage caveat: both reconciler files are parse_partial at scattered lines (none covering :441–508/:5584–5599); cited ranges read directly.
