<!-- capsule-v2 -->
# Throttler continueAsNew economics — where does an infinite workflow cut its event history, and why the 1-tick sleep before snapshotting?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** how does a queue workflow that never returns avoid unbounded event-history growth while never losing a job across the snapshot?

## Snapshot at empty-or-50, after a single-tick yield
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.throttle.ts` (:392-403); twin pattern in `workflow.enrichment.ts:194-198` (empty-or-**200**).
**Signature:** `continueAsNew({ nextAllowedAt, active, logged, q })` — full state passed as args to the fresh run.
**Data Shape:** the ENTIRE working set (queue array + gap deadline + flags) is serializable state; nothing durable lives outside the args.

### Decisive source
```ts
// prevent race condition if there are
await sleep(1);

if (q.length === 0 || q.length === 50) {
  return continueAsNew({
    nextAllowedAt: currentNextAllowedAt,
    active,
    logged,
    q,
  });
}
```

**Flow:** after each job completes → sleep(1) (a real durable timer tick) → if the queue just drained OR reached 50 items → replace this execution with a new one seeded from the snapshot.
**Invariant:** `await sleep(1)` is load-bearing: signal handlers that fired during job processing are delivered as events; without yielding first, a job enqueued between "splice head" and "return continueAsNew" could exist only in the dying history. The tick forces any in-flight enqueue event to land in `q` BEFORE it is serialized into the new run's args.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'await sleep(1)' apps/orchestrator/src/workflows/workflow.throttle.ts` → :393; enrichment twin `q.length === 0 || q.length === 200` → workflow.enrichment.ts:195.
**Why a porter gets it wrong:** cutting on `q.length === 0` alone means a hot queue NEVER snapshots (history grows forever); cutting at a fixed depth bounds worst-case replay cost per restart. The 50/200 depth is a replay-cost vs churn tradeoff — either number works, the bound is the point.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "continueAsNew", limit: 10, fields: ["lines"] });
```

## Verdict
Adopt: periodic full-state `continueAsNew` with an upper-bound depth trigger plus drain trigger, always preceded by a yield tick. Adapt thresholds to your event sizes. Omit nothing — this is runtime-shape logic, not product behavior.
