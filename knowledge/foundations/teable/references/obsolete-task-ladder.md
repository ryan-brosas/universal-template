<!-- capsule-v2 -->
# Obsolete-task completion ladder — when should a background task for a deleted/paused table succeed silently instead of failing?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** A queued recompute references a table that no longer exists (or is mid-provision) — how does the worker distinguish "work is obsolete, mark done" from "work is blocked, try later" from "real failure"?

## loadActiveTableForTask + NotFound handling in processComputedTask
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/worker/ComputedUpdateWorker.ts` — `LoadTaskTableResult` type (:121–131: `'loaded'|'blocked'|'completed'`), `loadActiveTableForTask` (:1104–1147), consumer ladder in `processComputedTask` (:936–961); seed twin at :692/:748 of spec.
**Signature:** `loadActiveTableForTask({task, tableId, context, logContext}): Promise<Result<LoadTaskTableResult, DomainError>>`.
**Data Shape:** Decision inputs: table existence via `TableByIdSpec`, provision state (provisioning/deleted), pause scopes; outcome per referenced table id.

### Decisive source
```ts
if (isNotFoundError(executeResult.error)) {
  const referencedTableIds = new Map<string, TableId>([
    [plan.seedTableId.toString(), plan.seedTableId],
    ...plan.steps.map((step) => [step.tableId.toString(), step.tableId] as const),
    ...plan.edges.flatMap((edge) => [
      [edge.fromTableId.toString(), edge.fromTableId] as const,
      [edge.toTableId.toString(), edge.toTableId] as const]),
    ...(plan.seedAllTableIds ?? []).map((tableId) => [tableId.toString(), tableId] as const),
  ]);
  for (const tableId of referencedTableIds.values()) {
    const tableResult = await this.loadActiveTableForTask({ task, tableId, context, logContext });
    if (tableResult.isErr()) { /* real failure -> handleTaskFailure */ }
    if (tableResult.value.status === 'completed') return ok(true); // obsolete work: DONE
    if (tableResult.value.status === 'blocked')   return ok(false); // paused/provisioning: requeue
  }
}
```

**Flow:** on NotFound escaping execution → collect the UNIQUE set of every table the plan references (seed, step targets, both ends of every edge, seedAll tables) → classify each: missing-and-deleted ⇒ 'completed' (the recomputation target is gone; failing would poison retries forever), present-but-not-active (paused scope or provisioning state) ⇒ 'blocked' (release and retry later), active ⇒ keep checking; only if a reference errors does the failure ladder engage.
**Invariant:** Deletion races MUST resolve to success, never error — an outbox task outliving its subject is NORMAL under eventual consistency, and treating it as failure burns attempts and dead-letters noise. The check walks BOTH edge endpoints because a plan may traverse tables not named in any step. Blocked-vs-completed must be evaluated per-table in deterministic order so one paused table doesn't mask another's deletion.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/worker/ComputedUpdateWorker.spec.ts` (:692 'releases seed tasks for retry when the seed table exists but is not active', :748 'completes obsolete seed tasks when the seed table no longer exists', :788 'completes obsolete planned tasks when a referenced table no longer exists').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "loadActiveTableForTask isNotFoundError LoadTaskTableResult", limit: 10 });
```

## Verdict
Adopt the three-way obsolete/blocked/failure classification over the full referenced-table closure, with deleted⇒markDone; adapt the activity predicate (provision state, pause registry) to host; omit teable-specific TableByIdSpec plumbing.
