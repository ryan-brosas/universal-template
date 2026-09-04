<!-- capsule-v2 -->
# Outbox health classification — what makes a durable-queue system degraded vs critical?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which signals compose into a health verdict for an outbox + broker pair?

## ComputedOutboxMonitorService
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-monitor.service.ts:ComputedOutboxMonitorService.collect` (:174–216; inspectQueue :246–297; refresh coalescing :153–164).
**Signature:** `getOverview({force?}): Promise<ComputedOutboxMonitorSnapshot>`.

### Decisive source
```ts
const reasons = this.healthReasons(queue, outbox);
const critical = reasons.some((reason) =>
  ['queue_unavailable', 'consumer_unavailable'].includes(reason));          // :178–180
const status: HealthStatus = critical ? 'critical'
  : reasons.length > 0 ? 'degraded' : 'healthy';
...
if (this.currentRefresh) return this.currentRefresh;                        // :154 coalesce
```

**Flow:** background timer samples every monitorIntervalMs; concurrent GETs COALESCE onto the in-flight promise (never stampede); queue inspection reads job counts + workers + recent completed/failed (payload re-validated through the wire schema, malformed → taskId 'unknown'); outbox side aggregates per-target counts across meta-fallback + BYODB with per-target error tolerance (`unavailableTargetCount`); zero workers ⇒ consumer_unavailable EVEN on producer-only roles (spec-pinned :220). Reasons: failed_jobs/dead_letters/stale_processing/overdue_pending degrade; only broker-down/consumer-zero are critical.
**Invariant:** Monitoring is read-only and never executes work. Partial data must still surface — one unavailable BYODB target yields 'degraded' with the rest of the data intact, not an error page.
**Probe:** `computed-outbox-monitor.service.spec.ts` ×5 (:41 freshness, :66 combined snapshot without executing a worker, :220 zero-workers-critical-on-producer-only, :287 BYODB partial degraded, :324 discovery-failure-not-healthy-empty).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "healthReasons", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-tier critical/degraded composition + refresh coalescing; adapt reason names; omit OTel gauge plumbing.
