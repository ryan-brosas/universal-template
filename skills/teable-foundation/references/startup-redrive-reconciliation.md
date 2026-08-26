<!-- capsule-v2 -->
# Startup redrive reconciliation — how do you re-arm durable tasks the broker may have lost while down?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a process recover wakeups after restart or Redis outage, cross-DB and cross-process?

## ComputedOutboxRedriveService
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-redrive.service.ts:ComputedOutboxRedriveService` (:77–291).
**Signature:** `onApplicationBootstrap(): void` → `runOnce({actionableOnly?}): Promise<void>`; per-target retry loop :205–225.

### Decisive keyset source
```ts
// data-db-client-manager.service.ts:342–348 — revision IS the dedup locator
revision: [
  new Date(row.updatedAt).getTime(),
  row.attempts,
  new Date(row.nextRunAt).getTime(),
  row.lockedAt ? new Date(row.lockedAt).getTime() : 0,
].join('-'),
// redrive.service.ts:209–210 — prefix bump defeats stale completed jobs
wakeupId: `cuwr2-${candidate.taskId}-${candidate.revision}`,
```

**Flow:** bootstrap ⇒ full scan (unless roles disabled); every 5min ⇒ actionable-only reconcile (due-pending + lease-expired processing); delivery-recovered event ⇒ another full pass. Cross-process exclusivity via `pg_try_advisory_lock(hashtext(key))` on a DEDICATED meta-DB connection (:373–389 manager); targets = meta-fallback PLUS every ready BYODB connection (:214–281) scanned with order-preserving bounded-concurrency map; candidates iterate keyset-paginated (`afterId`) with per-query timeouts; wakeup id = `cuwr2-<taskId>-<updatedAt.attempts.nextRunAt.lockedAt>` so any durable-state change yields a FRESH jobId (old completed cuwr-* jobs from pre-fix deploys can't dedup-shadow it). Failed targets retry in background with capped exponential backoff; actionable retries upgrade to full when a later full run also fails.
**Invariant:** Revision-in-the-id is what converts "state changed" into "new message" without broker cooperation. The redrive lock must live on the META db (always reachable) on its own pooled connection — advisory locks are connection-bound.
**Probe:** `computed-outbox-redrive.service.spec.ts` ×5 (:19 publish-all-under-lease, :71 consumer-only background recovery, :87 parked-task periodic reconcile, :138 retry upgrade, :180 both-disabled no-op).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ComputedOutboxRedriveService", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt revision-keyed replay ids + advisory-lock single-flight + multi-target iteration; adapt target discovery to your tenant topology; omit Nest lifecycle hooks.
