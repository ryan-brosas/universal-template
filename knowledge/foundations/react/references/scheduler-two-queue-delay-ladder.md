<!-- capsule-v2 -->
# Scheduler two-queue delay ladder — how do delayed tasks wait without blocking ready work, and when is a host timeout armed?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** Where does a task with `{delay: N}` live before its start time, and what exact conditions trigger the single host `setTimeout`?

## timerQueue / taskQueue split with re-sort on transfer
**Path/Symbol:** `packages/scheduler/src/forks/Scheduler.js:unstable_scheduleCallback` (:335–427), `advanceTimers` (:103–126), `handleTimeout` (:128–143).
**Signature:** `unstable_scheduleCallback(priorityLevel, callback, options?: {delay: number}): Task`; `advanceTimers(currentTime: number): void`.
**Data Shape:** Two module-level heaps (:79–80): `taskQueue` sorted by `sortIndex = expirationTime`, `timerQueue` sorted by `sortIndex = startTime`. A delayed task (`startTime > currentTime`, :395) goes to `timerQueue` with its delay as sortIndex; a ready task goes to `taskQueue` keyed by expiration.

### Decisive source
```js
} else if (timer.startTime <= currentTime) {
  // Timer fired. Transfer to the task queue.
  pop(timerQueue);
  timer.sortIndex = timer.expirationTime;
  push(taskQueue, timer);
```
Arming rule in `scheduleCallback`:
```js
if (peek(taskQueue) === null && newTask === peek(timerQueue)) {
  // All tasks are delayed, and this is the task with the earliest delay.
  if (isHostTimeoutScheduled) {
    // Cancel an existing timeout.
    cancelHostTimeout();
  } else {
    isHostTimeoutScheduled = true;
  }
  // Schedule a timeout.
  requestHostTimeout(handleTimeout, startTime - currentTime);
}
```

**Flow:** schedule(delayed) → timerQueue by startTime → if taskQueue empty AND this is the earliest timer, (re)arm exactly one host timeout for the delta → timeout fires `handleTimeout` → `advanceTimers` pops every fired/cancelled head, re-keying each survivor to expirationTime and pushing into taskQueue → if no host callback already scheduled, request one; else re-arm for the next remaining timer.
**Invariant:** At most one host timeout exists at any time (`isHostTimeoutScheduled`); a fired timer's priority position is computed from its expirationTime, NOT its original delay — that is why a UserBlocking task scheduled with `{delay: 100}` preempts Normal work the moment its delay elapses. The re-arm condition inside `handleTimeout` only schedules another callback if `!isHostCallbackScheduled`.

**Probe:** `packages/scheduler/src/__tests__/SchedulerMock-test.js` `'schedules a delayed task'` (:507–525): flush at t=0 and t=999 logs nothing; advancing 1ms past the 1000ms threshold flushes `['A']`. And `'interleaves normal tasks and delayed tasks'` (:558–589): UB timers at delays 100/300 interleave into normal work producing exactly `['A', 'Timer 1', 'B', 'C', 'Timer 2', 'D']`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "advanceTimers handleTimeout timerQueue delayed task", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the two-heap layout, the transfer-time re-sort, and the single-armed-timeout discipline as-is. Adapt the host timeout primitive to your platform's timer API. Omit profiling marks (`markTaskStart`/`isQueued`) unless porting the profiling plane too. Coverage caveat: `forks/Scheduler.js` is parse_partial (1–614 whole-file) at pin; all cited ranges read directly from source.
