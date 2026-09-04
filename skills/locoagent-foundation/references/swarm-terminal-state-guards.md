<!-- capsule-v2 -->
# Terminal-state write-once guards — how do completion, failure, and kill avoid overwriting each other and double-emitting SDK bookends?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** when a teammate can end via natural completion, thrown error, leader kill, or shutdown — what stops two paths from both finalizing the task?

## alreadyTerminal guard + notified:true pre-set + bookend protocol
**Path/Symbol:** `src/utils/swarm/inProcessRunner.ts:runInProcessTeammate` completion :1419-1461, catch/failure :1473-1525; `src/utils/swarm/spawnInProcess.ts:killInProcessTeammate` (:227-328).
**Signature:** `killInProcessTeammate(taskId, setAppState): boolean`.
**Data Shape:** terminal transitions all check `if (task.status !== 'running') { alreadyTerminal = true; return task }` INSIDE the state updater; killed tasks set `notified: true`.

### Decisive source
```ts
// killInProcessTeammate may have already set status:killed +
// notified:true + cleared fields. Don't overwrite (would flip
// killed → completed and double-emit the SDK bookend).
if (task.status !== 'running') {
  alreadyTerminal = true
  return task
}
// ...
// notified:true pre-set → no XML notification → print.ts won't emit
// the SDK task_notification. Close the task_started bookend directly.
if (!alreadyTerminal) {
  emitTaskTerminatedSdk(taskId, 'completed', { toolUseId, summary: identity.agentId })
}
```

**Flow:** every terminal path runs inside ONE state updater that: verifies still-running → invokes pending onIdleCallbacks → clears controllers/cleanup/messages-to-last-entry/pendingUserMessages → sets its own status (`completed` | `failed` | `killed`) → then OUTSIDE the updater: evictTaskOutput, evictTerminalTask, conditionally `emitTaskTerminatedSdk`, unregister perfetto agent. Kill additionally removes the member from teamContext.teammates keyed by agentId and from the team FILE after the updater ("outside state updater to avoid file I/O in callback").
**Invariant:** status guard makes first-writer-wins among competing terminals; `notified:true` is precisely the flag that suppresses the generic XML notification so exactly ONE SDK bookend closes per task; file I/O never happens inside a setState callback.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'double-emit the SDK bookend' src/utils/swarm/inProcessRunner.ts` (:1426-1427); `grep -n 'avoid file I/O in callback' src/utils/swarm/spawnInProcess.ts` (:301).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "killInProcessTeammate emitTaskTerminatedSdk evictTerminalTask", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt write-once terminal transitions guarded by current-status checks plus an explicit suppression flag paired with manual bookend emission; adapt status enums; omit perfetto tracing calls if untraced.
