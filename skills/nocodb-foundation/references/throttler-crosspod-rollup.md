<!-- capsule-v2 -->
# Cross-pod throttler rollup — how do N pods rate-limit-log a tenant once per window without a distributed lock?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What makes the leader election duplicate-safe when pods' clocks skew, and what degrades when Redis dies?

## INCRBY-everyone + SETNX-leader with 1.5x TTL
**Path/Symbol:** `packages/nocodb/src/helpers/throttlerLogger.ts:ThrottlerLogger` (whole 99L); singleton export `throttlerLogger` guarded by `Symbol.for('nocodb.throttlerLogger')`; consumer: global-exception.filter (ThrottlerException path).
**Signature:** `record({workspaceId?, baseId?}): void`; `flush(): Promise<void>`; module-level `setInterval(flush, 60_000).unref()`.
**Data Shape:** local buckets Map<`wsId?:baseId`, {count, firstSeenMs}>; Redis keys `throttler:count:<windowId>:<key>` / `throttler:leader:<windowId>:<key>`; REDIS_DEDUP_TTL_SECONDS = 90 = 1.5 × FLUSH_INTERVAL_MS.

### Decisive source
```ts
// Best-effort: every pod contributes to the shared counter, only the
// leader logs. The logged total reflects whatever pods had flushed
// before the leader's INCRBY — i.e. an approximate global count, not
// exact, but bounded above by the true total.
total = await NocoCache.incrbyExpiring('root', counterKey, bucket.count, REDIS_DEDUP_TTL_SECONDS);
isLeader = await NocoCache.setIfNotExist('root', leaderKey, '1', REDIS_DEDUP_TTL_SECONDS);
```
(:47–:65)

**Flow:** record() increments a per-process bucket keyed workspace:base → every 60s flush() swaps the map out (snapshot-and-clear so concurrent records land in the next window) and for each bucket computes windowId = floor(now/60s) → INCRBY adds this pod's count into the shared expiring counter; SETNX on the leader key elects exactly one logger per window → non-leaders skip logging entirely.
**Invariant:** the 90s TTL is 1.5× the flush interval SPECIFICALLY to absorb clock skew — a late pod whose flag expired after the early leader logged would emit a duplicate line if TTL were exactly one window. Approximate counts are the accepted contract (bounded above by true total). On cache failure, fall back to logging the LOCAL count as leader (worst case O(pods) duplicates, never signal loss). The Symbol.for global guard prevents setInterval leaks under nest watch/hot reload, and .unref() keeps the timer from holding the process open.
**Probe:** `cd packages/nocodb && grep -c "incrbyExpiring" src/helpers/throttlerLogger.ts` (=1) and `grep -c "setIfNotExist" src/helpers/throttlerLogger.ts` (=1) and `grep -c "Symbol.for" src/helpers/throttlerLogger.ts` (=1) and `grep -c "unref" src/helpers/throttlerLogger.ts` (=1 interval call; the no-hold-open rationale lives in a comment without the token).
**Direct test:** none upstream — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "ThrottlerLogger flush incrbyExpiring leader", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt counter-everywhere/leader-logs-once with skew-absorbing TTL and local-count degradation; adapt key prefixes/window to your observability stack; omit if you already run centralized metrics. Coverage caveat: grep-pinned only.
