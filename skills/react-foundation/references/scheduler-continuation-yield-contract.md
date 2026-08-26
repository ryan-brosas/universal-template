<!-- capsule-v2 -->
# Scheduler continuation yield contract — why must a returning task yield immediately even with budget left?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** What is the callback return-value protocol, and what must the loop do when a task returns a continuation function?

## Callback = boolean => ?Callback
**Path/Symbol:** `packages/scheduler/src/forks/Scheduler.js` type `Callback` (:47) and `workLoop` continuation branch (:218–231); consumer `packages/react-reconciler/src/ReactFiberRootScheduler.js:performWorkOnRootViaSchedulerTask` (:600–605).
**Signature:** `type Callback = boolean => ?Callback`; the boolean is `didUserCallbackTimeout`.
**Data Shape:** A task's `callback` field is replaced in place by its continuation; the Task object identity (and thus heap position/id tie-break) is preserved across slices.

### Decisive source
```js
const continuationCallback = callback(didUserCallbackTimeout);
currentTime = getCurrentTime();
if (typeof continuationCallback === 'function') {
  // If a continuation is returned, immediately yield to the main thread
  // regardless of how much time is left in the current time slice.
  currentTask.callback = continuationCallback;
  advanceTimers(currentTime);
  return true;
}
```

**Flow:** invoke callback → if it returns a function, store it as the task's new callback → return true from workLoop → flushWork returns true → host handler re-posts a fresh macrotask (`schedulePerformWorkUntilDeadline`) → continuation runs in a NEW browser task. Note `return true` exits workLoop before the normal pop/advance path, so no other task runs in this slice.
**Invariant:** A continuation always gets a fresh macrotask — even with the full frame budget unused — because the point is to let pending events/microtasks interleave between long-running chunks, not merely to bound blocking time. The scheduler never wraps or composes continuations; it just swaps the pointer.

**Probe:** `packages/scheduler/src/__tests__/Scheduler-test.js` `'yielding continues in a new task regardless of how much time is remaining'` (:320–351): the original task logs `shouldYield: false` (budget remains), returns a continuation, and the log still shows `'Post Message'`; `expect(performance.now()).toBe(0)` (:346) proves zero time elapsed yet the continuation ran in the next event. Consumer-side mirror: ReactFiberRootScheduler.js :600–604 returns `performWorkOnRootViaSchedulerTask.bind(null, root)` only while `root.callbackNode === originalCallbackNode`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "continuation callback yield workLoop hasMoreWork", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the return-a-function protocol and the unconditional yield-on-continuation rule. Adapt the boolean parameter to your own "did starve" signal (or drop it). Omit the reconciler-specific bind/callbackNode ownership check unless porting that consumer too. Coverage caveat: Scheduler.js parse_partial at pin; ranges read directly; test file no_recorded_issue.
