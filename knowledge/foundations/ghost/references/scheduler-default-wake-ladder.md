<!-- capsule-v2 -->
# Default scheduler wake ladder — how does an in-memory scheduler hit publish times within a second?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What timing constants and tombstone mechanics make the default (non-external) scheduler accurate without waking every job constantly?

## SchedulingDefault
**Path/Symbol:** `ghost/core/core/server/adapters/scheduling/scheduling-default.ts:SchedulingDefault` (:20–259; `_addJob` :45–77; `_execute` :96–141; `_pingUrl` :143–211; `run` :213–248; `unschedule` :254–258).
**Signature:** `schedule(job)`, `unschedule(job, opts?: {bootstrap?})`, `run()`, `_pingUrl(job): Promise`.
**Data Shape:** `allJobs: Record<timestampMs, SchedulerJob[]>` kept key-sorted; `deletedJobs: Record<"url_ms", SchedulerJob[]>` tombstones. Constants: `runTimeoutInMs = 1000*60*5`, `offsetInMinutes = 10`, `beforePingInMs = -50`, `retryTimeoutInMs = 5000`, `maxTries = 30`.
### Decisive source
```ts
_addJob: if (moment(timestamp).diff(moment(), 'minutes') < this.offsetInMinutes) { instantJob[timestamp] = [job]; this._execute(instantJob); return; }
_execute: const timeout = setTimeout(function () {
    (function retry() { const immediate = setImmediate(function () {
        if (moment().diff(moment(Number(timestamp))) <= self.beforePingInMs) { return retry(); }
        ...
        if (self.deletedJobs[deleteKey]) { ...pop-or-delete...; return; }
        self._pingUrl(job);
    }); })(); }, diff - 70);
_pingUrl: if (statusCode === 404) return;                       // post deleted already
      if (statusCode === 503 && tries < maxTries) setTimeout(() => { job.tries++; this._pingUrl(job); }, retryTimeoutInMs);
```
**Flow:** jobs <10min out execute immediately → others queue sorted by timestamp; the 5-min `run()` sweep moves soon jobs into execution → each timestamp wakes at `diff−70ms`, then spin-loops via setImmediate until within −50ms BEFORE the time → tombstone check → ping.
**Invariant:** (1) Wake-early-then-spin: setTimeout fires ~70ms early, setImmediate loop re-checks until inside a 50ms pre-window — precision without timer spam. (2) Tombstones are counted (`pop` per delete) so multiple same-key jobs survive independent deletions. (3) 404 is success-by-no-op (post deleted while queued); ONLY 503 retries, capped at 30 tries × 5s; publishing in the past adds `force:true` (body for PUT, query for GET). (4) HTTP client is an instance property (`this.request`) specifically so tests can stub it without importing cacheable-lookup's process-wide singleton. (5) `rescheduleOnBoot = true`; boot rebuild is driven by PostScheduling.rescheduleAll through the base adapter's allSettled fan-out.
**Probe:** `grep -cF "offsetInMinutes = 10" ghost/core/core/server/adapters/scheduling/scheduling-default.ts` → expect `1`; `grep -cF "beforePingInMs = -50" ghost/core/core/server/adapters/scheduling/scheduling-default.ts` → expect `1`; `grep -cF "maxTries = 30" ghost/core/core/server/adapters/scheduling/scheduling-default.ts` → expect `1`; `grep -cF "diff - 70" ghost/core/core/server/adapters/scheduling/scheduling-default.ts` → expect `1`; `grep -cF "force: true" ghost/core/core/server/adapters/scheduling/scheduling-default.ts` → expect `2` (json + searchParams arms); direct tests: `grep -cF "it('pingUrl (PUT, and detect publish in the past)'" ghost/core/test/unit/server/adapters/scheduling/scheduling-default.test.js` → `1` and `grep -cF "delete job (unschedule)" ghost/core/test/unit/server/adapters/scheduling/scheduling-default.test.js` → `2` (it + time-null variant).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "SchedulingDefault _execute _pingUrl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wake-early-spin pattern, counted tombstones, and the 404/503/force error ladder with all constants as a coherent set. Adapt storage to persistent queues for multi-process hosts (this scheduler is single-process in-memory).
