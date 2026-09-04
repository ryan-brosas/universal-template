<!-- capsule-v2 -->
# Computed-field outbox worker claims — how do N workers claim background recompute tasks without deadlocking Postgres or double-running work?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a multi-worker task queue built on plain Postgres rows claim, lease-renew, and complete work so that a stuck worker can never stall the fleet?

## Lease-based outbox with try-or-skip advisory locks
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/outbox/ComputedUpdateOutbox.ts:ComputedUpdateOutbox.claimBatch` (926–1103), `.renewLease` (1490–1527), `.markDone` (1541–1640), `.enqueueOrMerge` (443+, try-lock merge comment ~464); config `outbox/IComputedUpdateOutbox.ts:defaultComputedUpdateOutboxConfig` (seedInlineLimit 5000, maxAttempts 8, baseBackoffMs 5000, lockUnavailableRetryDelayMs 250, processingLeaseMs, heartbeatIntervalMs, reclaimBatchSize, maxConcurrentProcessingPerBase…).
**Signature:** `claimBatch(params: ClaimBatchParams /*{workerId, limit, now?}*/, context?): Promise<Result<ReadonlyArray<AnyOutboxItem>, DomainError>>`; `renewLease(params /*{taskIds, leaseOwner}*/): Result<string[]>` (actually-renewed ids); `markDone(taskOrId): Result<boolean>`.
**Data Shape:** outbox row: `{id, status: 'pending'|'processing'|..., next_run_at, estimated_complexity, locked_at, locked_by, attempts, plan_hash, base_id, seed_table_id, change_type}`; seed payloads spilled to a side table keyed by `task_id`. Claim owner string is derived from `workerId`.

### Decisive source
```ts
// claimBatch — try-or-skip global claim lock
const claimLockAcquired = await tryAcquireOutboxAdvisoryLock(
  trx, OUTBOX_CLAIM_ADVISORY_LOCK_KEY, 'claim_global');
if (!claimLockAcquired) {
  // Try-or-skip: another node inside a claim round means work is being drained;
  // parking every worker's claim behind one holder is how a single stuck claim
  // transaction stalls the whole fleet. Pending tasks are re-driven by their own
  // wakeups and the periodic redrive sweep.
  this.logger.debug('computed:outbox:claim_skipped_lock_busy', {...});
  return ok({ tasks: [], activity: null });
}
// 1) reclaim stale leases FIRST (bounded by reclaimBatchSize)
.where('o.status', '=', 'processing')
.where(sql<boolean>`("locked_at" is null or "locked_at" <= ${reclaimBefore})`)
.orderBy('locked_at', 'asc').limit(reclaimLimit).forUpdate().skipLocked()
// 2) fill remaining capacity from pending, cheapest-first
.orderBy('o.estimated_complexity', 'asc').orderBy('o.next_run_at', 'asc')
.limit(remaining).forUpdate().skipLocked()
// 3) stamp ownership
.updateTable(OUTBOX_TABLE).set({ status: 'processing', locked_at: now,
  locked_by: claimOwner, updated_at: now }).where('id', 'in', ids)
```

**Flow:** every claim round runs in ONE transaction: try-advisory-lock (lose ⇒ empty batch, never wait) → select stale `processing` rows whose `locked_at` expired (`now − processingLeaseMs`) bounded by `reclaimBatchSize` → select `pending` rows due (`next_run_at <= now`) filtered by pause/concurrency predicates, ordered `estimated_complexity` then FIFO → dedupe by scope (`dedupeClaimRowsByScope` :111) → space-pause filter (SQL-side when meta==data db, app-side otherwise) → `UPDATE … SET status='processing', locked_at, locked_by` → hydrate seeds → project activity → publish activity event AFTER the transaction commits. Workers hold a LEASE, not ownership: `renewLease` heartbeats `locked_at` only for rows still `status='processing' AND locked_by=me` and returns the ids it actually renewed — absence = lost lease. Completion deletes the row guarded by the same owner predicate.
**Invariant:** losing any lock race must NEVER park the caller's transaction — an empty result is always acceptable because wakeups/redrive re-drive pending work; a worker whose lease expired loses authority silently (its later `markDone` deletes 0 rows and must NOT touch activity state — the new owner owns the lifecycle); reclaimed work is bounded per round so a flood of stale rows cannot starve fresh pending work.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/outbox/__tests__/ComputedUpdateOutbox.nonblocking.pg.integration.spec.ts::"skips the claim round without waiting while another session holds the global claim lock"` (:284), `::"enqueues without waiting while another session holds the merge lock"` (:260), `::"still merges duplicate enqueues when the merge lock is free"` (:251); `__tests__/ComputedUpdateOutbox.claim.spec.ts::"returns immediately when the per-base claim lock is busy"` (:68).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "ComputedUpdateOutbox claimBatch renewLease", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lease+heartbeat worker-queue shape: try-or-skip advisory locks, stale-reclaim-before-pending, owner-stamped claims, renewal returning renewed ids, owner-guarded delete-on-complete, and post-commit activity projection; adopt the config surface (lease/reclaim/backoff/fanout knobs). Adapt lock-key namespaces, complexity ordering, and the seed side-table to your schema. Omit teable's computed-field semantics (plan hashes, seed splitting) unless building field recomputation. Caveat: `ComputedUpdateOutbox.ts` is parse_partial at exactly lines 2528/3008/3012/3016 (outside every cited range); coverage metadata otherwise matches HEAD.
