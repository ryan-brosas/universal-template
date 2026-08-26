<!-- capsule-v2 -->
# Solid MessageChannel scheduler — how does enableScheduling time-slice pure work with a 5ms frame budget?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 provenance refresh: originally authored against the retired `ext-solid` graph at the identical pin; retrieval re-executed on `solid` 2026-08-25, gen 2026-08-25T20:12:15Z). **Question:** How does the optional scheduler yield to the host, and what are its ordering and cancellation contracts?

## scheduler.ts: port of React's scheduler core
**Path/Symbol:** `packages/solid/src/reactive/scheduler.ts` (whole file :1-177): `setupScheduler` (:33-96), `enqueue` (:98-113), `requestCallback` (:115-137), `cancelCallback` (:139-141), `flushWork`/`workLoop` (:143-177).
**Signature:** `requestCallback(fn: () => void, options?: { timeout: number }): Task`; `cancelCallback(task: Task)`; `enableScheduling(scheduler = requestCallback)` on the signal side installs it.
**Data Shape:** `Task { id, fn: ((didTimeout) => void) | null, startTime, expirationTime }`; module state `taskQueue`, `isCallbackScheduled`, `isPerformingWork`, `yieldInterval = 5`, `maxYieldInterval = 300`.

### Decisive source
```ts
const channel = new MessageChannel(),
    port1 = channel.port1 as MessagePortWithUnref,
    port = channel.port2 as MessagePortWithUnref;
// In Node.js, active MessageChannel listeners keep the event loop alive.
if (typeof port1.unref === "function") port1.unref();
...
function workLoop(initialTime: number) {
  let currentTime = initialTime;
  currentTask = taskQueue[0] || null;
  while (currentTask !== null) {
    if (currentTask.expirationTime > currentTime && shouldYieldToHost!()) break;
    const callback = currentTask.fn;
    if (callback !== null) {
      currentTask.fn = null;
      const didUserCallbackTimeout = currentTask.expirationTime <= currentTime;
      callback(didUserCallbackTimeout);
      currentTime = performance.now();
      if (currentTask === taskQueue[0]) taskQueue.shift();
    } else taskQueue.shift();
    currentTask = taskQueue[0] || null;
  }
  return currentTask !== null;
}
```

**Flow:** first `requestCallback` lazily constructs a MessageChannel; scheduling posts a message → `port1.onmessage` sets `deadline = now + 5ms` (+ `maxDeadline = now + 300ms`) and runs `workLoop`, re-posting while work remains → tasks run in `expirationTime` order via binary-search `splice` insert (`enqueue`) → a task whose deadline expired runs with `didTimeout=true` → cancellation is LAZY: `cancelCallback` only nulls `task.fn`; the loop shifts it off when reached. Error path: onmessage re-posts and RETHROWS so the error escapes into a fresh host task instead of killing the port.
**Invariant:** `isInputPending`-capable hosts may skip yielding between deadlines unless the 300ms hard cap hits; without it, yield every 5ms frame. Node keeps running because both ports are `unref()`ed — omit that on browsers (guarded by feature check). Only ONE flush is ever scheduled at a time (`isCallbackScheduled && !isPerformingWork` gate).
**Probe:** `grep -c 'yieldInterval = 5' packages/solid/src/reactive/scheduler.ts` → `1`. Decisive test ranges in `test/scheduler.spec.ts` (whole file is 45 lines): :14-35 "queue a task in correct order" pins BOTH the FIFO default and priority inversion — three callbacks enqueued as (no-opts, timeout:10, timeout:40) run in exactly that order with count assertions 2→1→2, i.e. shorter timeout wins regardless of enqueue order; :37-44 "supports cancelling a callback" pins lazy cancellation — `cancelCallback(task)` before any flush and the rejected callback never fires while a later-enqueued task completes.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "requestCallback workLoop shouldYieldToHost MessageChannel", limit: 10 });
```

## Verdict
Adopt as the time-slicing substrate for transition queues under load. Adapt the host callback (setTimeout/setImmediate where MessageChannel is unavailable). Omit `isInputPending` refinement on non-browser targets.
