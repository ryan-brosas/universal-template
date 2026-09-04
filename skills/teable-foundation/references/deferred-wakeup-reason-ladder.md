<!-- capsule-v2 -->
# Deferred-wakeup reason ladder — how should a queue consumer reschedule a claim miss per failure class?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What delay and job id does each claim-miss reason get, and why?

## resolveDeferredWakeup
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-wakeup.handler.ts:resolveDeferredWakeup` (:62–113; constants :32–41; admission defer :48–55; outcome flow :187–282).
**Signature:** `resolveDeferredWakeup(taskId, currentWakeupId, eligibility, nowMs): {wakeupId, availableAt}`.

### Decisive source
```ts
case 'not_due':
  // releaseForRetry already chose the safe retry instant (250ms for computed lock misses).
  // Do not inflate it to the old generic two-second claim-race delay.                  // :85–87
  availableAt = retryAt && retryAt.getTime() > nowMs ? retryAt : transientRetryAt;
  break;
...
if (currentWakeupId === baseWakeupId || currentWakeupId.startsWith(`${baseWakeupId}-r`)) {
  availableAt = new Date(Math.max(availableAt.getTime(), nowMs + TRANSIENT_DEFER_DELAY_MS));
  return { availableAt,
    wakeupId: `${baseWakeupId}-r${Math.floor(availableAt.getTime() / TRANSIENT_DEFER_DELAY_MS)}` }; // :102–107
```

**Flow:** eligibility → delay: eligible/concurrency ⇒ 100ms transient (worker drains siblings post-commit; lease expiry is NOT the blocker's ETA); not_due ⇒ trust the durable layer's retryAt verbatim (never inflate); active_lease ⇒ max(transient, lease expiry); paused-with-retryAt ⇒ that instant; paused-indefinite (`retryAt===null`) ⇒ PARKED — no republish at all (:57–60, :238–247). Wakeup ids are DETERMINISTIC time-bucketed locators (`cuwd-<taskId>-<bucket>`) so duplicates converge on the same BullMQ jobId; same-id collision forces a `-r<bucket>` suffix with pushed-forward availability instead of swallowing the retry.
**Invariant:** Delays encode distributed-system facts, not vibes: short where another worker will drain (concurrency), exact where upstream computed one (not_due), never for indefinite pauses. Deterministic ids + delayed jobs give idempotent at-least-once delivery without duplicate storms.
**Probe:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-wakeup.handler.spec.ts` ×19 specs (:316 replay-on-miss, :365 lock-miss retryAt preserved, :389 fast concurrency, :413 eligible race, :432 lease expiry, :456 indefinite park, :498 finite pause once).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveDeferredWakeup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reason→delay ladder + deterministic bucketed ids; adapt constants to your broker; omit metrics calls.
