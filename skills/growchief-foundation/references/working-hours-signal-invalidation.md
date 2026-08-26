<!-- capsule-v2 -->
# Working-hours signal invalidation — how does a workflow sleeping until tomorrow's window learn that working hours changed mid-day?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** cached schedule + long sleep = stale config; what is the wake-up protocol?

## Refetch flag flipped by a Temporal signal handler
**Path/Symbol:** `apps/orchestrator/src/utils/working.hours.manager.ts:WorkingHoursManager` (whole class, :15-54); pure math in `shared/both/utils/time.functions.ts` (`isWithinWorkingHours` :63-89, `getTimeUntilWorkingHours` :1-61).
**Signature:** `new WorkingHoursManager(botId)`; `ensureWithinWorkingHours(): Promise<void>`; signal `workingHoursUpdated = defineSignal('workingHoursUpdated')`.
**Data Shape:** `WorkingHoursState = { workingHours: number[][]; timezone: number }` — Monday-first array of `[startMinutes, endMinutes]`, empty array = disabled day; `timezone` is whole-hour UTC offset. Default seed when unset: `[[540,1020],[540,1020],[540,1020],[540,1020],[540,960],[],[]]` (bots.service.ts getBotStatus).

### Decisive source
```ts
setHandler(workingHoursUpdated, () => {
  this.shouldRefetchWorkingHours = true;
  this.cachedWorkingHours = null;
});
async ensureWithinWorkingHours(): Promise<void> {
  while (true) {
    if (this.shouldRefetchWorkingHours || !this.cachedWorkingHours) {
      this.cachedWorkingHours = await getWorkingHours(this.botId); // activity
      this.shouldRefetchWorkingHours = false;
    }
    const { workingHours, timezone } = this.cachedWorkingHours;
    if (!isWithinWorkingHours(workingHours, timezone)) {
      const sleepTime = getTimeUntilWorkingHours(workingHours, timezone);
      await condition(() => this.shouldRefetchWorkingHours, sleepTime);
      continue;   // re-check with fresh hours after either wake cause
    }
    break;
  }
}
```

**Flow:** outside window ⇒ compute ms until window opens (7-day scan over days 0..6, skip disabled days; "today before start" vs "future day" both target next day-start; nothing found ⇒ 24h fallback) ⇒ `condition(refetchFlag, sleepTime)` wakes EITHER because an admin saved new hours and the API signaled every running throttler/bot-jobs workflow (`updateBotWorkingHours` lists `WorkflowType IN("workflowBotJobs","userWorkflowThrottler") AND ExecutionStatus="Running"` and signals each), OR because the timer expired.
**Invariant:** the sleep is never trusted as the source of truth for schedule changes — the boolean refetch flag checked by BOTH the condition predicate and the loop head makes a mid-sleep config change override the timer; local time math shifts `Date.now()` by `timezone*3600_000` then reads UTC getters, so no tz database is needed.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'shouldRefetchWorkingHours' apps/orchestrator/src/utils/working.hours.manager.ts` → :19/:35/:36/:45/:48; signal fan-out query → bots.service.ts:107-110.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "ensureWithinWorkingHours workingHoursUpdated", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt: cache-with-invalidation-flag + dual-cause condition (signal beats timer). Adapt hour encoding to your scheduler (cron strings would need the same flag). Omit the hardcoded default business-hours matrix if your product differs.
