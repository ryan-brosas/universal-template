<!-- capsule-v2 -->
# Task lease heartbeat — how does a worker notice mid-task that another worker stole its claim?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do long-running claimed tasks renew their leases and abort cleanly when the lease is lost, without a second worker executing the same task?

## ClaimedTaskLeaseManager
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/worker/ComputedUpdateWorker.ts:361–472` — `ClaimedTaskLeaseManager` (constructor :363–374, `start` :376–381, `stop` :383–391, `releaseTask` :393–400, `ensureTaskActive` :402–409, `heartbeat` :411–422, `runHeartbeat` :424–457, `groupTaskIds` :459–472).
**Signature:** `new ClaimedTaskLeaseManager(tasks: AnyOutboxItem[], outbox, logger, heartbeatIntervalMs)`; `ensureTaskActive(taskId): Promise<boolean>`; `runHeartbeat(taskIds?): Promise<void>` via `outbox.renewLease({taskIds, leaseOwner}): Result<string[], DomainError>` (returns ids actually renewed — owner-stamped).
**Data Shape:** Internal state: `taskOwners: Map<taskId, lockedBy>`, `lostTaskIds: Set<taskId>`, one `setInterval` timer, single in-flight `heartbeatPromise`.

### Decisive source
```ts
async heartbeat(taskIds?: string[]): Promise<void> {
  if (this.taskOwners.size === 0) return;
  if (this.heartbeatPromise) {
    await this.heartbeatPromise;      // join the in-flight beat instead of stacking a second
    if (!taskIds) return;
  }
  this.heartbeatPromise = this.runHeartbeat(taskIds).finally(() => { this.heartbeatPromise = null; });
  await this.heartbeatPromise;
}
// runHeartbeat groups by owner and treats renew results as a set difference:
const renewedIds = new Set(renewResult.value);
const lostIds = ids.filter((id) => !renewedIds.has(id));
// lost ids are evicted from taskOwners AND blacklisted in lostTaskIds
```

**Flow:** constructed from the claim batch (owner = each task's `lockedBy`) → `start()` begins interval heartbeats only while ≥1 owner exists → before processing EACH task, `ensureTaskActive` joins any pending heartbeat then re-checks the blacklist → lost tasks log `computed:worker:task_skipped_lost_lease`, release, and skip → after each task `releaseTask` evicts it and stops the timer at zero → `stop()` clears the interval and awaits the final heartbeat.
**Invariant:** Heartbeats must be SERIALIZED (single promise), never concurrent per worker. A failed renewal never throws — it demotes the task locally so THIS worker stops working on it; the DB lease row is the sole arbitration of ownership (a stolen task's work is discarded by the loser, not rolled back — execution idempotence comes from the lock ladder + markDone owner check).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/worker/ComputedUpdateWorker.spec.ts` (:1291 'renews leases while a long-running task is still processing', :1349 'skips claimed tasks that lose their lease before processing starts').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ClaimedTaskLeaseManager ensureTaskActive runHeartbeat", limit: 10 });
```

## Verdict
Adopt the join-don't-stack heartbeat, owner-grouped batch renewal with renewed-set diffing, local eviction + blacklist on loss, and liveness re-check immediately before each unit of work; adapt the renewal RPC shape to host; omit teable-specific logging keys.
