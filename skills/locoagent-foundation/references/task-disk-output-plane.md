<!-- capsule-v2 -->
# TaskOutput disk plane — how does background-task output travel through files and symlinks instead of memory streams?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How is task output persisted, how do readers tail it with resumable offsets, and what does initTaskOutputAsSymlink achieve?

## File-backed output with offset-based deltas + transcript symlink aliasing
**Path/Symbol:** `src/utils/task/diskOutput.ts`: `getTaskOutputPath`, `initTaskOutput`, `initTaskOutputAsSymlink`, `appendTaskOutput`, `getTaskOutputDelta`, `evictTaskOutput`; consumer side `src/utils/task/TaskOutput.ts` (TaskOutput.stopPolling :97-103).
**Signature:** `getTaskOutputDelta(taskId: string, offset: number): Promise<{ content: string; newOffset: number }>`; `initTaskOutputAsSymlink(taskId: string, target: string): Promise<void>`.
**Data Shape:** every TaskStateBase carries `outputFile` (path from id at creation) + `outputOffset` (reader cursor). Agent/main-session tasks symlink their output file to the agent transcript JSONL so one write serves both surfaces; remote tasks pre-create a real file because they append text deltas directly.

### Decisive source
```ts
// framework.ts generateTaskAttachments — the read side:
if (taskState.status === 'running') {
  const delta = await getTaskOutputDelta(taskState.id, taskState.outputOffset)
  if (delta.content) {
    updatedTaskOffsets[taskState.id] = delta.newOffset
  }
}
// LocalAgentTask registerAsyncAgent — the write-side alias:
void initTaskOutputAsSymlink(agentId, getAgentTranscriptPath(asAgentId(agentId)))
```

**Flow:** spawn initializes the output file (real or symlinked to transcript) → producers append (ShellCommand's TaskOutput, remote appendTaskOutput of serialized deltas, per-message sidechain writes) → framework poller reads ONLY the unread slice via the stored offset → offsets patched back under fresh-state re-validation (see task-evict-zombie-patch) → terminal+notified tasks get evictTaskOutput to reclaim disk.
**Invariant:** Output lives on disk precisely so backgrounded work survives UI eviction and process restarts; holding it in AppState would recreate the whale-session memory blowups documented in InProcessTeammateTask/types.ts. The offset must advance ONLY after content is consumed, and eviction requires notified=true or unread output would be silently destroyed. Symlinking output→transcript means /clear's re-link logic can move the target without breaking open readers.
**Probe:** `grep -n 'getTaskOutputDelta' src/utils/task/diskOutput.ts` (:304) and `grep -n 'export function initTaskOutputAsSymlink' src/utils/task/diskOutput.ts` (:427) and `grep -c 'evictTaskOutput' src/tasks/LocalShellTask/LocalShellTask.tsx` (4).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getTaskOutputDelta initTaskOutputAsSymlink", limit: 5 });
```

## Verdict
Adopt disk-backed output + offset deltas + transcript symlinking verbatim for any long-lived background surface. Adapt path layout to your storage roots. Omit nothing — eviction-without-notification is the trap.
