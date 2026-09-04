<!-- capsule-v2 -->
# Shell-task lifecycle — how does one completion handler serve spawn-time backgrounding, in-place backgrounding, and the killed race?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What are the three registration paths for a bash task, and how does each avoid double SDK events and leaked cleanup?

## Data-through-TaskOutput; three entrypoints converge on one result handler
**Path/Symbol:** `src/tasks/LocalShellTask/LocalShellTask.tsx:180-252`: `spawnShellTask`; :259-287: `registerForeground`; :420-474: `backgroundExistingForegroundTask`; :290-368 private `backgroundTask`; :515-522 `flushAndCleanup`.
**Signature:** `spawnShellTask(input: LocalShellSpawnInput & { shellCommand: ShellCommand }, context: TaskContext): Promise<TaskHandle>`.
**Data Shape:** taskId comes FROM `shellCommand.taskOutput.taskId` ("TaskOutput owns the data — use its taskId so disk writes are consistent"); state holds runtime-only `shellCommand`/`unregisterCleanup` fields that are nulled on terminal transitions.

### Decisive source
```ts
// Data flows through TaskOutput automatically — no stream listeners needed.
// Just transition to backgrounded state so the process keeps running.
shellCommand.background(taskId)
const cancelStallWatchdog = startStallWatchdog(...)
void shellCommand.result.then(async result => {
  cancelStallWatchdog()
  await flushAndCleanup(shellCommand)
  let wasKilled = false
  updateTaskState<LocalShellTaskState>(taskId, setAppState, task => {
    if (task.status === 'killed') {
      wasKilled = true
      return task            // kill won the race — keep its terminal state
    }
    ...
```

**Flow:** (1) `spawnShellTask` = born-backgrounded (registers + immediately backgrounds); (2) `registerForeground` = registers only, no watchdog/result handler — foreground ownership lives with the caller until user/timer backgrounds it; (3) `backgroundExistingForegroundTask` = in-place flip for the auto-background-timer path WITHOUT re-registering ("avoiding duplicate task_started SDK events and leaked cleanup callbacks"). All completion handlers treat status==='killed' at resolution time as the winning terminal state (`wasKilled`) and still enqueue a killed-flavored notification via the shared latch. Cleanup functions captured inside updaters are invoked OUTSIDE them ("avoid side effects in updater").
**Invariant:** Exactly ONE of these paths may attach the completion handler per task; re-registration must never happen for an existing id (duplicate task_started + orphaned cleanup). The kill-vs-exit race resolves by reading status INSIDE the result handler's updater — never assume which landed first.
**Probe:** `grep -n "does NOT re-register the task" src/tasks/LocalShellTask/LocalShellTask.tsx` (:413-414) and `grep -n "no stream listeners needed" src/tasks/LocalShellTask/LocalShellTask.tsx` (:218) and `grep -cn "avoid side effects in updater" src/tasks/LocalShellTask/LocalShellTask.tsx` (2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "spawnShellTask registerForeground", limit: 5 });
```

## Verdict
Adopt the three-path split + single-handler rule verbatim. Adapt ShellCommand/TaskOutput to your process wrapper. Omit monitor-kind summary wording unless you carry monitors.
