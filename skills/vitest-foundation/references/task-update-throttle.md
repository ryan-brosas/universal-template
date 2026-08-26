<!-- capsule-v2 -->
# Task update throttling — how does a worker stream thousands of task-state updates to the main process without flooding IPC?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How are per-task result packs coalesced for transport while guaranteeing no final update is ever lost?

## Throttled pack flush
**Path/Symbol:** `packages/vitest/src/runtime/runner/run.ts:sendTasksUpdateThrottled` (525), `throttle` (504–522), `sendTasksUpdate` (479–497), `finishSendTasksUpdate` (499–502), `updateTask` (527–531); module-level buffers `packs`, `eventsPacks`, `pendingTasksUpdates` (475–477).
**Signature:** `function throttle<T extends (...args: any[]) => void>(fn: T, ms: number): T`; interval pinned to the summary reporter's `DURATION_UPDATE_INTERVAL_MS` = 100ms.
**Data Shape:** `packs: Map<string, [TaskResult | undefined, TaskMeta]>` — keyed by task id so repeated updates to one task COALESCE (last write wins); `eventsPacks: [string, TaskUpdateEvent, undefined][]` — append-only ordered event log.

### Decisive source
```ts
// throttle based on summary reporter's DURATION_UPDATE_INTERVAL_MS
const sendTasksUpdateThrottled = throttle(sendTasksUpdate, 100)

function throttle(fn, ms) {
  let last = 0
  let pendingCall: ReturnType<typeof setTimeout> | undefined
  return function call(this: any, ...args: any[]) {
    const now = unixNow()
    if (now - last > ms) {
      last = now
      clearTimeout(pendingCall)
      pendingCall = undefined
      return fn.apply(this, args)
    }
    // Make sure fn is still called even if there are no further calls
    pendingCall ??= setTimeout(call.bind(this), ms, ...args)
  } as any
}

function sendTasksUpdate(runner) {
  if (packs.size) {
    const taskPacks = Array.from(packs).map<TaskResultPack>(([id, task]) => [id, task[0], task[1]])
    const p = runner.onTaskUpdate?.(taskPacks, eventsPacks)
    if (p) {
      pendingTasksUpdates.push(p)
      // remove successful promise to not grow array indefinitely,
      // but keep rejections so finishSendTasksUpdate can handle them
      p.then(() => pendingTasksUpdates.splice(pendingTasksUpdates.indexOf(p), 1), () => {})
    }
    eventsPacks.length = 0
    packs.clear()
  }
}
```

**Flow:** every state change calls `updateTask` → appends the event, overwrites the id-keyed pack entry, triggers the throttled flush → leading-edge immediate send when idle; under load at most one send per 100ms with a trailing timer that fires even if updates stop → `finishSendTasksUpdate` awaits all in-flight transport promises before the run finishes.

**Invariant:** (1) events keep ORDER and are never dropped; only result packs deduplicate by id; (2) the trailing timer guarantees the LAST update always lands (a pure leading-edge throttle would lose it); (3) in-flight send promises are retained until settle so the worker never exits before the final ack — rejections stay observable, resolutions are spliced out to bound memory.

**Probe:** exercised indirectly by every e2e reporter test (`test/e2e/test/reported-tasks.test.ts` asserts full callback sequences arrive intact despite throttling); unit pinning of ordering lives in `test/unit/test/execution-order.test.ts`. Coverage caveat: probe files read on disk at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "sendTasksUpdate throttle packs eventsPacks finishSendTasksUpdate", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.runtime.runner.run.sendTasksUpdateThrottled / .finishSendTasksUpdate
```

## Verdict
Adopt the id-coalescing map + ordered-event-log + trailing-timer throttle + await-all-in-flight close pattern for any high-frequency state streaming. Adapt interval and transport (postMessage/RPC/WS) to the host. Omit OTel span recording wrapped around sends.
