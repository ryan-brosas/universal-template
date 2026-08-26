<!-- capsule-v2 -->
# Agenda run completion races — how do you close a run exactly once when completion, cancellation, and failure can interleave?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** how do you guarantee a run reaches exactly one terminal state and the task follows, when cancel can land mid-`startSession` and session outcomes arrive asynchronously?

## Terminal-status guards across `runTask` tail, `cancelTask`, `finishRun`, `finishRunFailure`
**Path/Symbol:** `sdk/packages/core/src/tasks/agenda-task-manager.ts` — `TERMINAL_RUN_STATUSES` :36-41; post-start re-verify :720-757 in `runTask` :662-782; `cancelTask` :608-660; `finishRun` :813-870; `finishRunFailure` :872-902.
**Signature:** `private finishRun(task, run, sessionId): Promise<void>` / `private async finishRunFailure(task, run, error): Promise<void>`.
**Data Shape:** terminal set is closed: `completed | failed | cancelled | interrupted`. Every closer first re-reads the run row from the store; stale closers become no-ops.

### Decisive source
```ts
// after `await runtime.startSession(...)` — re-read before trusting the start:
const latestRun = this.store.getRun(run.runId);
const latestTask = this.store.getTask(taskId);
if (!latestRun || TERMINAL_RUN_STATUSES.has(latestRun.status) ||
    latestTask?.status !== current.status ||
    latestTask.currentRunId !== run.runId) {
    if (latestRun && !TERMINAL_RUN_STATUSES.has(latestRun.status)) {
        this.store.updateRun(run.runId, { status: "cancelled",
            sessionId: started.sessionId, completedAt: nowIso(),
            error: "Task changed or was cancelled while its session was starting." });
    }
    ...
    await this.runtime.abortSession(started.sessionId,
        "Agenda task was cancelled while its session was starting").catch(...);
    throw new Error(`task ${taskId} changed or was cancelled while starting`);
}
```
```ts
// finishRunFailure — exactly-once + stolen-run detection:
const latestRun = this.store.getRun(run.runId);
if (!latestRun || TERMINAL_RUN_STATUSES.has(latestRun.status)) return;
...
if (latestTask.currentRunId !== run.runId) {   // someone else owns/close the task now
    this.activeRuns.delete(task.taskId);
    this.publish("task.run.failed", latestTask, finalRun);
    return;                                     // never touch task state
}
```

**Flow:** every async boundary (post-startSession, session outcome, thrown error) re-fetches the run; if it went terminal while awaiting, the closer exits without writing. Cancelled-during-start marks the run cancelled, aborts the just-created session with a stable reason string, deletes `activeRuns`, and re-throws so no caller sees success. `finishRun` maps outcome → completed / `cancelTask` / failure, and its `finally` unconditionally clears `activeRuns`, fires fire-and-forget `reconcileScope` (failures logged, not thrown), and `queueAutomation`.
**Invariant:** a run transitions to a terminal status at most once; the loser of any race becomes a pure observer (publish at most, never mutate); a started-but-rejected session is always aborted — sessions never outlive their run record.
**Probe:** `agenda-task-manager.test.ts` "does not revive a task cancelled while its session is starting" (:117-158): `startSession` parked on a promise, `cancelTask` completes mid-start, late resolve ⇒ run rejects "cancelled while starting", `runSession` never called, `abortSession("late-session", …)` exact args, task stays `cancelled` with no currentRunId.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "TERMINAL_RUN_STATUSES finishRun finishRunFailure agenda", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.finishRunFailure" });
```

## Verdict
Adopt the pattern: closed terminal set + re-read-after-await + loser-becomes-observer + guaranteed compensation (`abortSession`) for orphaned side effects. Adapt the status names, reason strings, and event names to your host. Omit Cline's specific reconcile-on-finally coupling unless your tasks also have a file projection to refresh. Runner caveat: vitest not executable here (no node_modules); evidence = direct test read (:117-158) + byte-exact probes.
