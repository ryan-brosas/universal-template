<!-- capsule-v2 -->
# Atomic notified check-and-set — how do five task types share one duplicate-notification latch without a lock?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the exact idempotence pattern that stops a completion and a kill from both enqueuing a task_notification?

## Flag flip INSIDE the state updater decides enqueue
**Path/Symbol:** `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx:189-202`: `markTaskNotified` (boolean-returning variant); same pattern inline in `LocalShellTask.tsx:105-122` (`enqueueShellNotification`), `LocalAgentTask.tsx:224-240`, `LocalMainSessionTask.ts:231-243`; void-flipper variant `LocalShellTask.tsx:481-486`: `markTaskNotified`.
**Signature:** `(taskId, setAppState) => boolean` — true iff THIS call flipped the flag (caller should enqueue), false if already notified.
**Data Shape:** `notified: boolean` lives on TaskStateBase; flipping it and observing the flip happen in ONE synchronous updater pass is the whole mechanism.

### Decisive source
```ts
function markTaskNotified(taskId, setAppState): boolean {
  let shouldEnqueue = false
  updateTaskState(taskId, setAppState, task => {
    if (task.notified) {
      return task            // already consumed — no-op reference return
    }
    shouldEnqueue = true
    return { ...task, notified: true }
  })
  return shouldEnqueue
}
```

**Flow:** any notification-producing path calls this first → only the winner enqueues its XML `<task_notification>` → losers (kill racing completion, TaskStopTool racing natural exit) silently skip. Kill paths that pre-set `notified: true` in their own state update deliberately suppress the later completion notification but then emit `emitTaskTerminatedSdk(...)` directly so SDK consumers still see the bookend close (stopTask.ts :67-95 documents exactly which suppressions carry payload vs noise).
**Invariant:** The check-and-set must be atomic inside ONE updater invocation. Reading `task.notified`, then deciding outside, then setting later is a TOCTOU — two racing paths both see false and the model receives doubled notifications. NOTE the name collision: LocalShellTask exports a VOID `markTaskNotified(taskId,setAppState)` while RemoteAgentTask's private one returns boolean — port the boolean contract, don't trust the name alone.
**Probe:** `grep -n "Atomically check and set" src/tasks/LocalShellTask/LocalShellTask.tsx` (:106) and `grep -n "Returns true if this call flipped" src/tasks/RemoteAgentTask/RemoteAgentTask.tsx` (:186-187).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "markTaskNotified", limit: 5 });
```

## Verdict
Adopt the single-updater check-and-set verbatim. Adapt the flag name/placement to your state base. Omit the SDK bookend re-emit unless you have an equivalent consumer stream.
