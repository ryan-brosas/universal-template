<!-- capsule-v2 -->
# Outbox worker execution loop — how does a claimed background task execute, stage forward, and fail without ever stalling or double-executing?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the exact claim→execute→stage→complete lifecycle of one outbox task, and which failure classes requeue vs dead-letter?

## ComputedUpdateWorker.runOnce + processComputedTask
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/worker/ComputedUpdateWorker.ts` — `runOnce` (:508–590), `processClaimedTask` (:731–746), `processComputedTask` (:748–984), `planNextStage` (:1645–1737), `splitLargeComputedTask` (:1149–1180), failure ladder (:928–973).
**Signature:** `runOnce({workerId, limit, actorId?, tracer?, requestId?}): Promise<Result<number, DomainError>>`; per-task phases tracked in `failurePhase: 'deserialize_plan'|'set_statement_timeout'|'collect_seed_field_ids'|'collect_seed_table_ids'|'acquire_locks'|'execute_plan'|'publish_events'|'collect_dirty_seed_groups'|'plan_next_stage'|'enqueue_next_stage'|'mark_done'`.
**Data Shape:** Task item carries serialized plan (steps/edges/seeds), `runId`, `originRunIds`, `runTotalSteps`, `runCompletedStepsBefore`, `stageDepth`. Result of a task: `true` processed / `false` skipped-requeue.

### Decisive source
```ts
// Lock-unavailable and not-found are CONTROL FLOW, not failures:
if (isComputedUpdateLockUnavailable(executeResult.error)) {
  await this.releaseTaskForRetry(computedTask, ..., this.outboxConfig.lockUnavailableRetryDelayMs);
  return ok(false); // no attempt consumed
}
if (isNotFoundError(executeResult.error)) {
  // walk every referenced table; 'completed' => obsolete task, done silently;
  // 'blocked' => table paused/provisioning, requeue
}
// Everything else: classify -> non-retryable forces dead letter with diagnostics
const failure = classifyComputedTaskFailure(executeResult.error);
await this.handleTaskFailure(computedTask, ..., {
  forceDeadLetter: !failure.retryable, failure,
  diagnostics: buildFailureDiagnostics(executeResult.error, failure, failurePhase),
});
```

**Flow:** claimBatch → per task: lease-manager liveness check → split-if-too-large (fan-out chunks enqueue + original markDone BEFORE any lock acquisition) → deserialize plan → single `withTransaction`: SET LOCAL statement_timeout → acquire try-advisory locks (`wait:false`) → updater.execute with `lockWait:false` ("overlapping writers requeue instead of overwriting computed columns with stale concurrent snapshots") → build+publish events via afterCommit hook → collectDirtySeedGroups → planNextStage → enqueue next stage at `stageDepth+1` (hard cap `MAX_STAGE_DEPTH = 50` logs-and-skips) → markDone. Events publish AFTER commit through `registerAfterCommit(context, publish)` — inside-txn publishes are deferred, never dropped.
**Invariant:** Lock-miss requeues MUST NOT consume attempt budget toward the dead letter (starving tasks surface only via the 5-minute `task_requeue_starvation` age warning). Next-stage planning DOWNGRADES changeType insert/delete→update ("follow-up stages recompute surviving records... not replaying original row deletion/insertion semantics") and MERGES before-images carried from the original mutation — dropping them forces conditional edges into whole-table mode.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/worker/ComputedUpdateWorker.spec.ts` (:365 statement-timeout→dead letter, :486 lock-unavailable→release-for-retry, :788 obsolete-task completion on missing table, :831 large-task split before locks, :997 event publishing deferred until commit, :1110 insert→update downgrade, :1291 lease renewal during processing, :1349 skip tasks that lost their lease).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "processComputedTask runOnce ClaimedTaskLeaseManager planNextStage", limit: 10 });
```

## Verdict
Adopt the phase-tagged failure ladder (control-flow requeue vs classified dead-letter), stage-depth cap, before-image carry-forward, afterCommit event publication, and pre-lock task splitting; adapt config knobs (timeouts, delays) and error-code predicates to host; omit ShareDB request-id plumbing details if host has no realtime layer.
