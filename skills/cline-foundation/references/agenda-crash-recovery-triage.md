<!-- capsule-v2 -->
# Agenda crash-recovery triage — what happens to in-flight runs when the hub restarts or stops?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** after a crash, which interrupted runs get their approval back, and which degrade — and why does recovery run before any file reconciliation?

## `recoverInterruptedRuns` + startup ordering + graceful `dispose`
**Path/Symbol:** `sdk/packages/core/src/tasks/agenda-task-manager.ts:1178-1222` (`recoverInterruptedRuns`); call site in `start()` :295-299; `dispose()` :319-351.
**Signature:** `private recoverInterruptedRuns(): void` (sync, store-only).
**Data Shape:** scans `listRuns({ status: ["starting","running"], limit: 1000 })`; every hit is marked `interrupted`; the owning task is then triaged by run status and revision equality.

### Decisive source
```ts
if (
    run.status === "starting" &&
    task.approvedRevision === run.taskRevision &&
    task.revision === run.taskRevision &&
    !this.isExpired(task)
) {
    // approval survived; only the session link died → restore to approved
    this.store.updateTaskState(task.taskId, {
        status: "approved", currentRunId: null,
        error: "Hub restarted before this task session was linked.",
        updatedBy: TASK_MANAGER_ACTOR,
    });
    continue;
}
this.store.updateTaskState(task.taskId, {
    status: run.status === "starting" ? "pending_approval" : "failed",
    approvedRevision: run.status === "starting" ? null : task.approvedRevision,
    currentRunId: null,
    error: "Hub restarted while this task was running.",
    updatedBy: TASK_MANAGER_ACTOR,
});
```

**Flow:** `start()` marks itself started, calls `recoverInterruptedRuns()` FIRST (:299), and only then reconciles global/workspace projections, expires stale tasks, starts the unref'd 30 s maintenance timer (`expireTasks` + `queueAutomation`). Recovery rule: all non-terminal runs → `interrupted`; tasks already terminal just lose their `currentRunId`; a `starting` run whose task revision AND approvedRevision both equal `run.taskRevision` and that hasn't expired is restored to `approved` (re-runnable without re-approval); everything else degrades — `starting` ⇒ `pending_approval` with approval revoked (never auto-resume work the user never saw running), `running` ⇒ `failed` keeping approvedRevision. `dispose()` mirrors recovery for graceful stop: abort live sessions, `await Promise.allSettled(this.backgroundRuns)`, then mark remaining actives `interrupted`/`failed` ("Hub task manager stopped before the run completed.") and close the store only if owned.
**Invariant:** recovery precedes projection reconciliation so no reconciler can resurrect a half-dead run; restoration requires exact revision identity on both counters — any edit between approve and crash voids the restore; a crashed process can never leave a task pointing at a dead run.
**Probe:** `agenda-task-manager.test.ts` "recovers a crash during session startup back to approved" (:833-885): fixture writes spec + creates task + approves + creates run + latches currentRunId by hand (simulating crash mid-link), new manager `.start()` ⇒ task `{ status: "approved", currentRunId: undefined }`, run row `{ status: "interrupted" }`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.recoverInterruptedRuns" });
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.dispose" });
```

## Verdict
Adopt the triage table (terminal→unlink; starting+revision-identical+unexpired→approved; else starting→pending_approval / running→failed) and recovery-before-reconciliation startup order. Adapt the revision-identity check to whatever your approval token is pinned to. Omit the unref'd maintenance timer if your host has its own scheduler, but keep expiry idempotent. Runner caveat: vitest not executable here (no node_modules); evidence = direct test read (:833-885) + byte-exact probes.
