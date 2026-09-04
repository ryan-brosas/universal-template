<!-- capsule-v2 -->
# Dirty-target lock choreography — why seed-only advisory locks are insufficient for hybrid computed writers

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do concurrent computed-update tasks (different seeds, same write targets) avoid overwriting each other's computed columns with stale values?

## Lock the POST-propagation dirty set, reusing the seed lock planner
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedFieldUpdater.ts` — `acquireDirtyTargetLocks` (:652–706) with load-bearing doc comment :644–651; dirty-group collection `collectDirtyRecordGroupsForLocks` (:1791–1831); call site in `executePreparedSteps` :867–874 ("Serialize concurrent hybrid/async writers that touch the same target rows"); planner reuse trick :687–693 (`seedRecordIds: [], extraSeedRecords: dirtyGroups`).
**Signature:** `acquireDirtyTargetLocks(plan, context, prepared: PreparedDirtyState, options?: {wait?: boolean; logContext?}): Promise<Result<ComputedUpdateLockSummary, DomainError>>`.
**Data Shape:** reads back the FULL dirty table `(table_id, record_id)` after propagation and regroups into `ComputedSeedGroup[] {tableId, recordIds[]}` (re-validating via `TableId.create`/`RecordId.create`); empty state returns a zeroed `{mode:'none', …, batchShardCount}` summary.

### Decisive source
```ts
/**
 * Lock every dirty target record (or batch/table fallback) before writeback.
 *
 * Seed-only locks do not serialize tasks that write the same cascade targets from
 * different seed tables. Holding target locks for the write transaction forces
 * overlapping hybrid workers to requeue (wait=false) or wait (wait=true) instead of
 * overwriting each other's computed columns with stale values.
 */
async acquireDirtyTargetLocks(plan, context, prepared, options?) {
  if (prepared.totalDirtyRecords === 0 || prepared.dirtyStats.length === 0) return ok(zeroSummary);
  const dirtyGroups = await this.collectDirtyRecordGroupsForLocks(prepared.db);
  // ...
  const lockPlan: ComputedUpdatePlan = {
    ...plan,
    // Dirty groups are the write targets; reuse the seed lock planner without
    // re-locking the original seed list (those are acquired separately).
    seedRecordIds: [],
    extraSeedRecords: dirtyGroups,
  };
  return this.acquireLocks(lockPlan, context, { wait: options?.wait,
    logContext: { ...options?.logContext, lockScope: 'dirty_targets', ... } });
}
```
**Flow:** `execute()` → `prepareDirtyState` seeds + propagates the frontier → `executePreparedSteps` FIRST acquires dirty-target locks (record→batch-shard→table escalation handled by the existing lock planner — see capsule `computed-update-lock-ladder`) → then executes steps; with `wait:false` an unavailability error (`COMPUTED_UPDATE_LOCK_UNAVAILABLE_CODE`) tells the outbox worker to REQUEUE the task rather than block.
**Invariant:** the lock set is observed AFTER propagation (it covers cascade targets, not just seeds), and it is acquired on the SAME connection/transaction that performs the writes — otherwise the mutual exclusion is fictional. Two tasks seeded from different tables but cascading onto one target serialize here; skipping this step is the classic stale-overwrite bug in fan-out recompute designs. Note the deliberate split: seed locks (pre-execution, cheap) + dirty-target locks (post-propagation, precise) are complementary, not redundant.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedFieldUpdater.spec.ts` — `"uses try advisory locks when the caller requests non-blocking lock acquisition"` (:773). Escalation semantics pinned by `__tests__/ComputedUpdateLock.spec.ts` (capsule `computed-update-lock-ladder`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "acquireDirtyTargetLocks", limit: 5 });
// → ComputedFieldUpdater.acquireDirtyTargetLocks …/record/computed/ComputedFieldUpdater.ts 652-706
```

## Verdict
Adopt "lock what you will WRITE, derived from post-propagation state, inside the write transaction" as the pattern; adopt the planner-reuse move (`extraSeedRecords = dirty groups`) to avoid a second lock-plan implementation. Adapt key shapes to your advisory-lock budget (see lock-ladder capsule for FNV shard keys). Omit tracing wrappers. Coverage caveat: only try-advisory behavior is directly tested at this level; wait-mode ordering is exercised indirectly through worker specs.
