<!-- capsule-v2 -->
# Periodic bucket quota ladder — how do you enforce a daily API cap that still admits steady low-rate traffic after a burst?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you implement a rolling multi-granularity quota (day/hour/minute) where overflow spills into NEXT-period buckets instead of rejecting outright?

## Check day→hour→minute; each exhausted level re-targets its keys at the next finer period before rejecting
**Path/Symbol:** `app/server/lib/DocApi.ts:getDocApiUsageKeysToIncr` (:2348–2365), `docPeriodicApiUsageKey` (:2320–2325), `docApiUsagePeriods` (:2294–2310); consumer `DocApiUsageTracker._checkAndUpdateDailyUsageExceeded` (:119–150).
**Signature:** `getDocApiUsageKeysToIncr(docId: string, usage: LRUCache<string, number>, dailyMax: number, m: moment.Moment): string[] | undefined`; `docPeriodicApiUsageKey(docId, current: boolean, period, m)` returns `doc-${docId}-periodicApiUsage-${m.format(period.format)}`.
**Data Shape:** Three periods: day `YYYY-MM-DD` ×1/day, hour `YYYY-MM-DDTHH` ×24/day, minute `YYYY-MM-DDTHH:mm` ×1440/day. Keys embed UTC time so old buckets simply stop being hit and LRU-evict — "daily measured usage conceptually 'resets' at UTC midnight". `periodMax = Math.ceil(dailyMax / periodsPerDay)` per level.

### Decisive source
```ts
const keys = docApiUsagePeriods.map(p => docPeriodicApiUsageKey(docId, true, p, m));
for (let i = 0; i < docApiUsagePeriods.length; i++) {
    const period = docApiUsagePeriods[i];
    const key = keys[i];
    const periodMax = Math.ceil(dailyMax / period.periodsPerDay);
    const count = usage.get(key) || 0;
    if (count < periodMax) { return keys; }
    // Allocation for the current day/hour/minute exceeded → use the NEXT day/hour/minute instead.
    keys[i] = docPeriodicApiUsageKey(docId, false, period, m);
}
// all three exhausted → undefined ⇒ reject
```
**Flow:** build current day/hour/minute keys → walk finest-last: if day has room, admit and increment ALL THREE current buckets; else rewrite the DAY key to tomorrow and retry against hour budget; else rewrite HOUR key too and retry minute; else `undefined` = 429. Tracker side always increments the local LRU first (burst protection without Redis), then mirrors via Redis MULTI `INCR+EXPIRE` (expiry = 2 periods so spill buckets live long enough) and adopts Redis counts when they come back higher.
**Invariant:** documented economics (in-source comment): steady low usage survives indefinitely even after a burst exhausts the day; a user can reach ~2× dailyMax on day one but then settles to steady rate. The returned array length/order is fixed (day,hour,minute) — the tracker zips it with `docApiUsagePeriods[i]` for expiry math, so never filter or reorder keys.
**Probe:** `test/server/lib/DocApiUsageTracker.ts:43–67` ("daily limits": "should reject when daily limit exceeded" :44, "should skip daily check when dailyMax is undefined" :58).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "docApiUsageKey getDocApiUsageKeysToIncr periodicApiUsage dailyMax", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the spill-to-next-bucket ladder for any quota that must degrade to a sustained rate instead of hard-rejecting after a burst. Adapt period set/formats freely — the invariant is only "finer levels get budgets derived from the coarsest". Omit the Redis mirror for single-worker cases.
