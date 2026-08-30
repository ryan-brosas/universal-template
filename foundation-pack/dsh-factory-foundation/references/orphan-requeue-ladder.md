<!-- capsule-v2 -->
# Orphan requeue ladder — how does a crashed process's work recover without exceeding its retry budget?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I detect runs orphaned by a dead owner and requeue or fail them by attempt count, without touching live sessions?

## requeueOrphanedRuns
**Path/Symbol:** `packages/domain/src/index.ts` (`FactoryDomain.requeueOrphanedRuns`) (:911–936).
**Signature:** `requeueOrphanedRuns(liveSessionIds: ReadonlySet<string>, protectedRunIds: ReadonlySet<FactoryRunId>, maxAttempts: number): Promise<FactoryStoreRead>`.
**Data Shape:** operates on `origin === 'scheduler'` runs in dispatching/running/waiting; `run.attempt` (per-task 1-based) is the retry counter; `maxAttempts` from scheduler config (default 3).

### Decisive source
```ts
if (run.origin !== 'scheduler' || !['dispatching', 'running', 'waiting'].includes(run.status) || protectedRunIds.has(run.id)) continue
if (run.sessionId !== undefined && liveSessionIds.has(run.sessionId)) continue
const task = document.tasks.find(candidate => candidate.id === run.taskId && candidate.activeRunId === run.id)
if (task === undefined) continue
run.status = 'failed'; run.failure = 'Owning Factory process or Session disappeared'; ...
if (task.automation?.trigger.kind === 'recurring' && task.automation.enabled) {
    task.status = 'scheduled'; task.failure = run.failure
} else if (run.attempt >= maxAttempts) {
    task.status = 'failed'; task.failure = run.failure
} else {
    task.status = 'queued'; delete task.failure
}
```

**Flow:** each leader tick passes the cross-process presence snapshot (`liveSessionIds`) and its OWN actively-monitored run ids as `protectedRunIds` → a scheduler-origin run whose session is gone AND not protected is failed with a fixed disappearance message → three-way landing: enabled-recurring tasks go back to `scheduled` (the schedule outlives crashes), attempts-exhausted go terminal `failed`, otherwise `queued` for re-dispatch.
**Invariant:** Observed-origin runs are NEVER requeued here (they belong to live user Sessions, reconciled elsewhere); protection set prevents the current process from failing runs it is mid-construction on; the attempt counter lives on the run so retries are per-attempt, not per-task-lifetime.
**Probe:** `packages/domain/tests/domain.spec.ts` "requeues one orphaned attempt and fails at the configured retry ceiling" (first disappearance → queued; at ceiling → failed). Deterministic from repo root: `grep -c "Owning Factory process or Session disappeared" packages/domain/src/index.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "requeueOrphanedRuns", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project: Function nodes rank-1 line-exact.)

## Verdict
Adopt the presence-based orphan detection + recurring/attempt/queue landing ladder + protection set. Adapt heartbeat/TTL plumbing to host presence infra. Omit observed-session reconciliation twin (separate seam capsule below).
