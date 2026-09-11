<!-- capsule-v2 -->
# Best-effort distributed lock — what should a Redis SET NX lock do when Redis disappears mid-flight?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do you write a multi-pod critical section that degrades to no-op instead of taking the deployment down — and never releases someone else's lock?

## Fail-open SET NX lock with owner-checked release
**Path/Symbol:** `apps/nestjs-backend/src/distributed-lock/distributed-lock.service.ts:DistributedLockService` (whole file, 83L): `runExclusive` (27–46), `acquire` (53–62), `release` (64–74); owner identity constructor field (~21).
**Signature:** `runExclusive(name: string, ttlSeconds: number, task: () => Promise<void>): Promise<boolean>` — resolves `true` if the task RAN, `false` if skipped.
**Data Shape:** key shape `` `lock:${name}` ``; value = per-process owner token `${pid}-${Date.now()}-${random}`; TTL in seconds via cache `setnx`.

### Decisive source
```ts
private async acquire(key, ttlSeconds): Promise<boolean> {
  // No Redis — no shared store to lock against; let the caller proceed.
  if (!this.usesRedis) return true;
  try {
    return await this.cacheService.setnx(key, this.owner, ttlSeconds);
  } catch (error) {
    this.logger.warn(`Failed to acquire lock "${key}", proceeding anyway`, error);
    return true;                                   // fail OPEN
  }
}
private async release(key): Promise<void> {
  ...
  // Only release a lock this instance still owns.   ← TTL may have expired and
  if ((await this.cacheService.get(key)) === this.owner) {  // another pod taken it
    await this.cacheService.del(key);
  }
}
```

**Flow:** `runExclusive` → acquire via SET NX with TTL → lost ⇒ log-and-return false (task SKIPPED, never queued) → won ⇒ run task in try/finally → release only-if-owner → return true. The class doc states the contract plainly: without Redis there is no shared store, so the lock degrades to no-op and every instance proceeds — callers must therefore keep the guarded work IDEMPOTENT.
**Invariant:** the lock is an optimization, never a correctness guarantee — guarded work MUST be idempotent because fail-open means duplicate execution is possible; release checks ownership before delete (a slow task whose TTL expired won't delete a newer holder's lock); skip semantics (false = didn't run) let schedulers treat contention as "someone else is doing it" rather than an error.
**Probe:** `apps/nestjs-backend/src/distributed-lock/distributed-lock.service.spec.ts::"runs the task when the lock is acquired"` (:22), `::"skips the task when another instance holds the lock"` (:34), `::"does not release a lock owned by another instance"` (:66), `::"runs the task anyway when acquiring the lock errors"` (:76).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "DistributedLockService runExclusive", limit: 5,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-open posture + owner-checked release + idempotency requirement as THE contract for cron/maintenance locks behind a cache you don't fully trust. Adapt the backend (any store with setnx), key namespace, and TTL defaults to host. Omit fencing-token rigor — this pattern deliberately trades strictness for availability; use the computed-update-outbox lease capsule instead when exclusivity actually matters for correctness.
