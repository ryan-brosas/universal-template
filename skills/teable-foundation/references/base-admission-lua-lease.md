<!-- capsule-v2 -->
# Per-base Redis lease admission — how do you cap concurrent outbox work per tenant with fail-closed Lua?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is per-base concurrency enforced across processes, and how does a worker know its slot died mid-operation?

## ComputedOutboxBaseAdmissionService
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-base-admission.service.ts:ComputedOutboxBaseAdmissionService.runWithPermit` (:90–183).
**Signature:** `runWithPermit<T>(baseId, operation(permit): Promise<T>): Promise<{admitted:false} | {admitted:true, value:T}>`.

### Decisive source
```lua
-- ACQUIRE_SCRIPT :16–25
local now = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', key, '-inf', now)
if redis.call('ZCARD', key) >= capacity then return 0 end
redis.call('ZADD', key, now + leaseMs, owner)
if redis.call('PTTL', key) < leaseMs * 2 then redis.call('PEXPIRE', key, leaseMs * 2) end
return 1
-- RENEW_SCRIPT :45–49
redis.call('ZADD', key, 'XX', now + leaseMs, owner)
```

**Flow:** capacity check + insert ATOMIC inside one Lua script using REDIS server TIME (never app clocks); key = `{queuePrefix}:{queue}:admission:{baseId}` with `{baseId}` hash-tag for cluster slot co-location; TTL kept ≥ 2×lease so an idle-but-live key never vanishes mid-lease; renewal every 10s via ZADD **XX** (update-only — cannot resurrect after expiry, spec-pinned "does not resurrect an owner whose Redis lease has expired"); renewals race a 5s timeout, failure/loss latches `leaseLost`; `permit.assertActive()` THROWS at every phase boundary (before container resolve, around worker run, between drain batches) aborting local work the moment ownership is doubtful; release removes own member and DELs empty keys.
**Invariant:** Fail-CLOSED on acquisition errors (spec: rejects with redisError); XX-only renewal means a partitioned worker cannot silently reclaim; assertActive-after-every-await converts silent lease loss into loud failure instead of double-processing.
**Probe:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-base-admission.service.spec.ts` (12 specs incl. :112 resurrect-block, :247 stall-stop, :231 Redis-time discipline).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "runWithPermit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt atomic-Lua zset leases + XX renewal + permit assertion; adapt key namespacing to your queue infra (keep the hash-tag); omit BullMQ client indirection.
