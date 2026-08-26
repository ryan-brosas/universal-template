<!-- capsule-v2 -->
# Scheduler priority expiration table — what timeout does each level get, and how does expiration override the yield check?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** What are the exact per-priority timeout constants, and under what condition does a task refuse to yield before the frame budget ends?

## Priority → timeout mapping and the expiration bypass
**Path/Symbol:** `packages/scheduler/src/forks/Scheduler.js:unstable_scheduleCallback` switch (:355–378) and `workLoop` yield gate (:193–203); `packages/scheduler/src/SchedulerPriorities.js:10–18`; `packages/scheduler/src/SchedulerFeatureFlags.js:10–18`.
**Signature:** `PriorityLevel = 0|1|2|3|4|5` (NoPriority=0 … IdlePriority=5); `timeout` is milliseconds added to `startTime`.
**Data Shape:** `expirationTime = startTime + timeout`; `maxSigned31BitInt = 1073741823` (Scheduler.js :76). Config at OSS pin: `frameYieldMs = 5`, `userBlockingPriorityTimeout = 250`, `normalPriorityTimeout = 5000`, `lowPriorityTimeout = 10000`, `enableRequestPaint = true`, `enableProfiling = false`, `enableAlwaysYieldScheduler = __EXPERIMENTAL__`.

### Decisive source
```js
case ImmediatePriority:
  // Times out immediately
  timeout = -1;
  break;
case UserBlockingPriority:
  // Eventually times out
  timeout = userBlockingPriorityTimeout;   // 250
...
case IdlePriority:
  // Never times out
  timeout = maxSigned31BitInt;
```
Yield gate in `workLoop`:
```js
if (!enableAlwaysYieldScheduler) {
  if (currentTask.expirationTime > currentTime && shouldYieldToHost()) {
    // This currentTask hasn't expired, and we've reached the deadline.
    break;
  }
}
```

**Flow:** schedule → pick timeout by priority → expiration = start + timeout → each loop iteration: if NOT yet expired AND host budget exhausted, break (yield); an expired task runs regardless of budget. `didUserCallbackTimeout = currentTask.expirationTime <= currentTime` (:212) hands that boolean to the callback.
**Invariant:** Priority ordering lives in the heap key (sortIndex=expiration), so "higher priority" means earlier expiration — it wins both when work is queued AND by refusing to yield once expired. ImmediatePriority's `-1` timeout makes it expired at birth. The consumer receives `didUserCallbackTimeout` rather than reading the clock itself.

**Probe:** `packages/scheduler/src/__tests__/ReactSchedulerIntegration-test.js` `'mock Scheduler module to check if shouldYield is called'` (:272–321): after `Scheduler.unstable_advanceTime(10000)` expires the task, React finishes B and C **without consulting shouldYield again** — the expiration-bypass branch in action. Constants cross-checked against `SchedulerFeatureFlags.js` read directly (:13–15).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "priority timeout expiration maxSigned31BitInt shouldYieldToHost", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the table shape (including −1 for immediate and 2³⁰−1 as "never") and the single boolean handed to callbacks. Adapt numeric timeouts to your product's latency targets — they are feature-flag constants, not laws. Omit `forceFrameRate`'s console['error'] evasion trick; keep its 0–125 fps clamp idea (:481–496). Coverage caveat: flags file is no_recorded_issue but was still read directly; Scheduler.js ranges read directly due to parse_partial.
