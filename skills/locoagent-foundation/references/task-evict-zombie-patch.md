<!-- capsule-v2 -->
# Terminal-task eviction & zombie-patch defense — how are finished background tasks GC'd without clobbering a concurrent status transition?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When does a terminal task leave AppState, and why must offset patches merge against fresh state?

## notified-gated eviction + offset-only patches + retain grace
**Path/Symbol:** `src/utils/task/framework.ts:125-144`: `evictTerminalTask`; :158-206: `generateTaskAttachments` (async scan); :213-249: `applyTaskOffsetsAndEvictions`.
**Signature:** `generateTaskAttachments(state): Promise<{ attachments, updatedTaskOffsets, evictedTaskIds }>`; `applyTaskOffsetsAndEvictions(setAppState, updatedTaskOffsets, evictedTaskIds): void`.
**Data Shape:** constants `POLL_INTERVAL_MS=1000`, `STOPPED_DISPLAY_MS=3_000`, `PANEL_GRACE_MS=30_000`. Eviction requires terminal status AND `notified===true`; `'retain' in task` narrows to LocalAgentTaskState and `(task.evictAfter ?? Infinity) > Date.now()` blocks eviction until the panel deadline passes.

### Decisive source
```ts
// Only the offset patch — NOT the full task. The task may transition to
// completed during getTaskOutputDelta's async disk read, and spreading the
// full stale snapshot would clobber that transition (zombifying the task).
updatedTaskOffsets: Record<string, number>
...
setAppState(prev => {
  ...
  for (const id of evictedTaskIds) {
    const fresh = newTasks[id]
    // Re-check terminal+notified on fresh state (TOCTOU: resume may have
    // replaced the task during the generateTaskAttachments await)
    if (!fresh || !isTerminalTaskStatus(fresh.status) || !fresh.notified) {
      continue
    }
```

**Flow:** poll loop snapshots tasks → async per-task disk delta reads → returns ONLY offset numbers + eviction candidate ids → applier re-reads FRESH prev.tasks and re-validates every condition before writing. `evictTerminalTask` is the eager variant (called right after notification enqueue); the lazy GC in generateTaskAttachments "remains as a safety net".
**Invariant:** Never spread a pre-await task snapshot back into state after an await — a completion that landed mid-await would be reverted and the task zombified (running forever with dead output). Every post-async write re-checks its precondition against fresh state.
**Probe:** `grep -n "zombifying the task" src/utils/task/framework.ts` (:162) and `grep -n "TOCTOU: resume may" src/utils/task/framework.ts` (:237) and `grep -n "remains as a safety net" src/utils/task/framework.ts` (:123).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "evictTerminalTask", limit: 5 });
```

## Verdict
Adopt the patch-don't-overwrite pattern verbatim — it is the general shape for any store write after async work. Adapt grace-period durations to your UI. Omit the attachment XML builder (framework's enqueueTaskNotification path is vestigial: each task type sends its own notifications).
