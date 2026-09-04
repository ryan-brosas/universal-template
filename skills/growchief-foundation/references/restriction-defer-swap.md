<!-- capsule-v2 -->
# Restriction defer-and-swap — when the head job hits a platform limit, how does the queue keep other action types flowing?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** a connection-request job is rate-limited until next week, but message/like jobs sit behind it in the queue — what is the exact choreography?

## Two branches on "is there another functionName in the queue?"
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.throttle.ts` (:196-240) + `apps/orchestrator/src/activities/workflow.information.activity.ts:getStepRestrictions/saveRestriction` (:168-187).
**Signature:** `getStepRestrictions(botId: string, methodName: string) → { until: Date } | null` (repository: `findFirst({ where: { botId, methodName, until: { gt: now } } })`, bots.repository.ts:554-567).
**Data Shape:** restrictions table rows keyed (botId, methodName) with an absolute `until` timestamp; the throttler checks BEFORE working hours/gap and only for the HEAD job's functionName.

### Decisive source
```ts
if (isRestrictions) {
  if (q.some((f) => f.functionName !== job.functionName)) {
    // OTHER TYPES EXIST: wait only until either the restriction ends
    // or a different-type job arrives — whichever comes first
    const sleepDuration = Math.max(0, isRestrictions.until.getTime() - Date.now());
    await condition(() => q.some((f) => f.functionName !== job.functionName), sleepDuration);
  } else {
    // ONLY THIS TYPE EXISTS: rotate — first different-type job to front,
    // push blocked job to the BACK stamped with the restriction end date
    await lock.runExclusive(async () => {
      q.splice(0, 1);
      const idx = q.findIndex((f) => f.functionName !== job.functionName);
      if (idx > -1) { const j = { ...q[idx] }; q.splice(idx, 1); q.unshift(j); }
      q.push({ ...job, date: isRestrictions.until.getTime() });
    });
  }
  continue; // re-enter loop; sortFunction puts the pushed job last via date
}
```

**Flow:** head restricted? → branch A (mixed queue): durable `condition(pred, deadline)` wakes early when a different-type job is signaled in, else at restriction end; loop re-examines the NEW head. Branch B (uniform queue): blocked job re-dated to `until` so the sort ladder naturally sinks it behind everything, and one different-type job (if any appeared meanwhile) is promoted to head.
**Invariant:** the blocked job is never dropped and never retried before `until` — its `date` field becomes the deferral mechanism; all queue surgery stays inside the same mutex as enqueue/remove so the rotation cannot race a concurrent signal.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'q.some((f) => f.functionName !== job.functionName)' workflow.throttle.ts` → :207/:213; repository gate `until: { gt: dayjs().utc().toDate() }` → bots.repository.ts:559-561.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "getStepRestrictions saveRestriction", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt: type-aware head-of-line bypass — never block unrelated action types behind a limited one; encode deferral AS a sort-key change rather than a timer list. Adapt the restriction source (page-banner detection here; any limiter signal works). Omit LinkedIn-specific weekly-limit messages.
