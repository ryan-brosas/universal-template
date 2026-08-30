<!-- capsule-v2 -->
# Agenda run admission gate ladder — how do you admit a run so staleness, expiry, and double-claims are impossible before any LLM session exists?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** what must be verified, and in what order, before a queued task is allowed to start an agent session?

## Run admission in `AgendaTaskManager.runTask`
**Path/Symbol:** `sdk/packages/core/src/tasks/agenda-task-manager.ts:662-782` (`AgendaTaskManager.runTask`); helpers `assertRevision` :1401-1410, `isExpired` :1174-1176.
**Signature:** `runTask(taskId: string, actor: AgendaTaskActor, expectedRevision: number, requestedByClientId?: string): Promise<{ task: AgendaTaskRecord; run?: AgendaTaskRunRecord }>`.
**Data Shape:** caller supplies the revision it saw; manager owns `activeRuns: Map<taskId, { runId, sessionId? }>` and the SQLite store; returns the latched task + starting run, or throws with a task-specific message.

### Decisive source
```ts
const current = await this.refreshAndVerifyTaskIntent(taskId);
this.assertRevision(current, expectedRevision);
if (this.isExpired(current)) {
    this.expireTask(current);
    throw new Error(`task ${taskId} has expired`);
}
if (Date.parse(current.availableAt) > Date.now()) {
    throw new Error(`task ${taskId} is not available yet`);
}
if (current.status !== "approved" && current.status !== "failed") {
    throw new Error(`task ${taskId} must be approved before it can run`);
}
if (current.approvedRevision !== current.revision) {
    throw new Error(`task ${taskId} approval is stale`);
}
if (this.activeRuns.has(taskId) || current.currentRunId) {
    throw new Error(`task ${taskId} already has an active run`);
}
let run = this.store.createRun({ taskId, taskRevision: current.revision, requestedByClientId });
```

**Flow:** sync intent reconcile → revision CAS check → expiry (expires instead of running) → availability window → status gate (approved|failed only) → approval-staleness gate → in-memory ∧ DB active-run gate → `createRun` (status `starting`, itself revision-checked) → `updateTaskState` latches `currentRunId`/`lastRunId` **before** `startSession`, then publishes `task.updated`.
**Invariant:** admission never mutates before every gate passes; the DB claim (`currentRunId`) is written before the side effect (`startSession`), so any concurrent observer sees the claim; a failed gate leaves zero artifacts. Expiry at admission demotes to `expired` rather than running doomed work.
**Probe:** `sdk/packages/core/src/tasks/agenda-task-manager.test.ts` "requires approval, links a session, and completes the task" (:84-115) — unapproved run rejects with "must be approved"; after `approveTask` the run starts, `lastSessionId` matches `/^session_run_/`, events `task.run.started`/`task.run.completed` fire.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "agenda task manager run lifecycle", limit: 10, fields: ["signature", "lines"] });
await mcp.codebase_memory.trace_path({ project: "cline", function_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.runTask", direction: "both", depth: 2 });
```
(Verified this pass: callers are exactly `pumpAutomation`/`queueAutomation` — automation reuses the same gate ladder.)

## Verdict
Adopt the ordered gate ladder with fail-closed messages, expire-at-admission, and claim-before-side-effect ordering. Adapt gate predicates to your host's status vocabulary and the intent source (Markdown spec vs your config). Omit Cline's specific refresh hook if you have no file-backed intent; keep *some* synchronous re-read so approvals cannot act on stale state. Runner caveat: upstream vitest not executable here (no node_modules) — evidence is direct test read + byte-exact probes.
