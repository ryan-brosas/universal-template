<!-- capsule-v2 -->
# Inline outbox drain loop — how does push-mode dispatch avoid double-draining while guaranteeing a cascading queue actually empties?

## single-flight inFlight guard + delayed timer + drain-until-empty-poll; external mode deliberately skips inline dispatch
**Path/Symbol:** `HybridWithOutboxStrategy.ts` — `scheduleDispatch(context)` (:511–543, external skip :513–519, timer single-flight :522–537, context strip :526–530 "Strip transaction… Preserve requestId for ShareDB src matching", delay≥50ms commit-race note :96/:532), `drainOutbox` (:545–577, `if (this.dispatchInFlight) return` :546, drain-until-empty :552–573 with T6191 comment). Companion capsules: `outbox-worker-lifecycle`, `computed-seed-dispatch`.
**Signature:** `scheduleDispatch(context): void`; `drainOutbox(context): Promise<void>` (private).

### Decisive source
```ts
if (this.config.dispatchMode === 'external') return;      // BullMQ owns delivery
if (this.dispatchTimer) return;                            // one pending timer only
const dispatchContext = { actorId, tracer, requestId };    // NO transaction field
this.dispatchTimer = setTimeout(() => {
  this.dispatchTimer = null;
  void this.drainOutbox(dispatchContext);
}, this.config.dispatchDelayMs);                           // ≥50ms: let the tx COMMIT first
...
private async drainOutbox(context) {
  if (this.dispatchInFlight) return;
  this.dispatchInFlight = true;
  try {
    let shouldContinue = true;
    while (shouldContinue) {
      const result = await this.worker.runOnce({ workerId, limit, ... });
      if (result.isErr()) { warn(...); shouldContinue = false; continue; }
      if (result.value <= 0) shouldContinue = false;       // empty poll ⇒ queue idle
    }
  } finally { this.dispatchInFlight = false; }
}
```

**Flow:** enqueue paths call scheduleDispatch → external mode exits (restart-safe default; the wake-up worker owns latency) → otherwise coalesce to ONE pending timer (repeated enqueues within the delay collapse) → after the delay, drain loops runOnce until an empty poll.
**Invariant:** FIVE details porters get wrong: (1) The timer delay is not cosmetic — dispatching before the enqueuing transaction commits makes the worker claim NOTHING (task invisible), silently dropping the cascade; 50ms is the documented floor. (2) The stripped context is deliberate: carrying the old `transaction` would run worker SQL on the (already finished) caller connection; requestId survives so realtime events keep ShareDB source attribution. (3) Drain continues past non-empty results because processing a task may ENQUEUE its next cascade stage — stopping after one batch strands deep link chains mid-propagation (T6191 dual-link regression). (4) The empty-poll termination is required precisely because claim counts can't be known up front. (5) Both guards (timer + inFlight) are needed: the timer coalesces scheduling storms, inFlight prevents concurrent drains when the timer fires during a running drain.
**Probe:** deterministic grep :534–537/:552–573; HybridWithOutboxStrategy.spec.ts covers dispatch modes.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "scheduleDispatch drainOutbox dispatchInFlight dispatchTimer", limit: 5 });
```
## Verdict
Adopt for any embedded outbox consumer: delayed single-flight dispatch with tx-stripped contexts and drain-until-empty semantics; keep an external-wakeup escape hatch as the production default.
