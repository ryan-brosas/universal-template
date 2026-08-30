<!-- capsule-v2 -->
# Scheduler error-resume macrotask — how does the queue survive a throwing task without a try/catch around user code?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** If a task callback throws, what must happen to the remaining queue, the reentrancy flags, and the exception itself?

## hasMoreWork sentinel + finally, no catch
**Path/Symbol:** `packages/scheduler/src/forks/Scheduler.js:performWorkUntilDeadline` (:498–528) and `flushWork` (:145–191).
**Signature:** `performWorkUntilDeadline: () => void` (MessageChannel/setImmediate handler); `flushWork(initialTime: number): boolean`.
**Data Shape:** Local mutable `hasMoreWork = true` before the guarded call; scheduler state to restore: `currentTask`, `currentPriorityLevel`, `isPerformingWork`.

### Decisive source
```js
// If a scheduler task throws, exit the current browser task so the
// error can be observed.
//
// Intentionally not using a try-catch, since that makes some debugging
// techniques harder. Instead, if `flushWork` errors, then `hasMoreWork` will
// remain true, and we'll continue the work loop.
let hasMoreWork = true;
try {
  hasMoreWork = flushWork(currentTime);
} finally {
  if (hasMoreWork) {
    // If there's more work, schedule the next message event at the end
    // of the preceding one.
    schedulePerformWorkUntilDeadline();
  } else {
    isMessageLoopRunning = false;
  }
}
```
And flushWork's unconditional restore:
```js
} finally {
  currentTask = null;
  currentPriorityLevel = previousPriorityLevel;
  isPerformingWork = false;
```

**Flow:** task throws → flushWork's finally clears `currentTask`/restores priority/clears `isPerformingWork` → exception propagates through performWorkUntilDeadline's finally, which still re-posts the next macrotask because `hasMoreWork` was never reassigned → the exception surfaces as an uncaught host error → next message event resumes with the rest of the queue.
**Invariant:** The queue is never corrupted by a throwing task: the failed task is simply abandoned mid-heap (its callback already nulled at :208), state flags always reset via finally, and the error is *reported, not swallowed*. Do not add a catch that logs-and-continues inside the same tick — the design deliberately exits the browser task first.

**Probe:** `packages/scheduler/src/__tests__/Scheduler-test.js` `'throws when a task errors then continues in a new event'` (:263–282): `expect(() => runtime.fireMessageEvent()).toThrow('Oops!')` while the log shows `['Message Event', 'Oops!', 'Post Message']` — the re-post happened during the throw — then the second `fireMessageEvent()` runs the surviving `'Yay'` task.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "flushWork performWorkUntilDeadline hasMoreWork errored task", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the sentinel+finally resume loop and the two-layer state restore exactly; they are environment-independent. Adapt where you route the surfaced error (window.onerror / process handler). Omit the profiling-only catch in flushWork (:162–176) unless porting profiling. Coverage caveat: parse_partial file read directly; test assertions quoted from the no_recorded_issue test file.
