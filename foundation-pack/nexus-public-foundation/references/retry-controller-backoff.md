<!-- capsule-v2 -->
# Retry backoff with jittered slots — how do you cap retries with exponential-but-jittered delays, avoid thundering herds, and expose an "excessive retries" health signal?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-transaction/.../RetryController.java`, `RollingStats.java`); Codebase Memory `nexus-public`. **Question:** How do I implement a bounded transaction-retry policy where delay grows exponentially per attempt, never collapses to zero for serious failures, and the system can report how often retries are being exhausted?

## Slot-doubling delay + rolling hourly counter
**Path/Symbol:** `public/common/components/nexus-transaction/src/main/java/org/sonatype/nexus/transaction/RetryController.java` — tunables (:41–66), `allowRetry` (:181–214), `updateExcessiveRetriesThreshold` (:227), `randomDelay` (:248–261); window math in `RollingStats.java:maybeShiftWindow` (:70–86).
**Signature:** `boolean allowRetry(final int retriesSoFar, final Exception cause)`; `private long randomDelay(final int nextRetry, final Exception cause)`; all knobs are system properties: `nexus.tx.retry.limit` (default 8), `.minSlots` 2, `.maxSlots` 256, `.minorDelay` 10ms, `.majorDelay` 100ms, `.majorExceptionFilter` (`IOException`), `.noisyExceptionFilter`.
**Data Shape:** `slots = clamp(1 << nextRetry, minSlots, maxSlots)`; a random slot in `[0, slots)` picks the delay; `excessiveRetriesHourlyStats` is a `RollingStats(60, MINUTES)` ring of per-minute counters; `excessiveRetriesThreshold = (retryLimit >> 1) + 1`.

### Decisive source
```java
if (nextRetry > retryLimit) { log.warn("Exceeded retry limit..."); return false; }
if (nextRetry == excessiveRetriesThreshold && !noisyExceptionFilter.test(cause)) {
  excessiveRetriesHourlyStats.mark();      // count each near-exhaustion ONCE
}
long delay = randomDelay(nextRetry, cause);
backoff(delay);                            // Thread.sleep; interrupt => RuntimeException
return true;

private long randomDelay(final int nextRetry, final Exception cause) {
  int slots = min(max(1 << nextRetry, minSlots), maxSlots);
  int randomSlot = randomHolder.get().nextInt(slots);
  if (majorExceptionFilter.test(cause)) {
    return majorDelayMillis * (randomSlot + 1);   // +1: never zero-wait on major failures
  }
  return minorDelayMillis * randomSlot;
}
```

```java
// RollingStats.maybeShiftWindow — circular buffer zeroing under double-checked lock
long newTick = currentTick();
if (tick < newTick) {
  synchronized (this) {
    if (tick < newTick) {
      rangeClosed(tick + 1, newTick).limit(buckets.length()).mapToInt(this::index).forEach(i -> buckets.set(i, 0));
      tick = newTick;
    }
  }
}
```

**Flow:** caller passes attempts-so-far → over-limit ⇒ warn + deny → at exactly the half-limit threshold mark the hourly ring (unless the exception class is whitelisted as noisy) → compute jittered delay from doubled slot count → sleep → allow. `sum()` of the ring (`excessiveRetriesInLastHour`) becomes the health/metrics surface. The ring lazily zeroes stale buckets only when time has advanced, guarded by a synchronized double-check.
**Invariant:** delay is EXPONENTIAL IN SLOTS but JITTERED within the slot count (decorrelated across threads ⇒ no synchronized retry storms); major-class failures (IO by default) get `randomSlot + 1` so the minimum wait is one major tick, while minor failures may legitimately wait 0ms. The threshold marker fires once per retry sequence (at `nextRetry == threshold`, not ≥), so the counter counts sequences nearing exhaustion, not individual attempts.
**Probe:** `nexus-transaction/src/test/java/org/sonatype/nexus/transaction/RetryControllerTest.java` — `testRetryLimit` (:62) pins the deny-at-limit boundary; `RollingStatsTest.java` pins window shift/sum arithmetic.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "RetryController allowRetry randomDelay RollingStats", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the slot-doubling jitter formula with the major/minor exception split and the once-per-sequence excessive-retry marker into a circular minute-ring. Adapt the property names, `ThreadLocalSplittableRandom` source, and Thread.sleep-based backoff to your scheduler. Omit the Guava `Time` plumbing. Boundary test verified on-disk at the pinned commit.
