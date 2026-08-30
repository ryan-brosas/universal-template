<!-- capsule-v2 -->
# Minute-ticker scheduler — how do I fire cron automations exactly once per minute wall-clock without double-fires or timer drift?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How does the daemon turn a wall-clock tick into at-most-one launch per automation per minute, and why is the fired-minute map pruned every tick?

## Aligned self-rescheduling setTimeout + minute-key dedupe
**Path/Symbol:** `packages/server/src/automation-scheduler.ts:AutomationScheduler.runTick` (36–61), `.scheduleNextTick` (63–73), `.start/.dispose` (22–34).
**Signature:** `runTick(now: Date = new Date()): void`; private `scheduleNextTick(): void`; emits `due: [Automation]` then `tick: [now: Date]`.
**Data Shape:** `lastFiredMinuteByAutomationId: Map<string, number>` where minuteKey = `Math.floor(now.getTime() / MS_PER_MINUTE)` (epoch minutes — sleep-safe, no Date math); `disposed` latch; unref'd timer.

### Decisive source
```ts
// :47-54 — match across ALL compiled crons, dedupe on epoch-minute key
const matched = compileScheduleAll(automation.trigger.schedule).some((expression) => {
  const parsed = parseCronExpression(expression);
  return parsed !== null && cronMatchesDate(parsed, now);
});
if (!matched) continue;
if (this.lastFiredMinuteByAutomationId.get(automation.id) === minuteKey) continue;
this.lastFiredMinuteByAutomationId.set(automation.id, minuteKey);
this.emit("due", automation);
```

**Flow:** `scheduleNextTick` computes delay = `MS_PER_MINUTE − (now % MS_PER_MINUTE) + AUTOMATION_TICK_ALIGNMENT_DELAY_MS` (constants.ts:701 = 50ms) so ticks land just AFTER each wall-clock minute boundary (a tick at :00.999 would mis-evaluate the previous minute's match), runs `runTick`, then re-arms itself — one timer alive, never an interval that drifts. Per tick: skip disabled/finished/non-schedule automations (watch+event triggers are owned by FolderWatchManager/SessionEventManager, never the ticker); a cron parse failure inside `.some()` simply doesn't match (invalid schedule ⇒ tolerable silence, valid siblings still fire). AFTER evaluation, prune map entries whose automation id no longer exists (deletions would otherwise leak). `tick` fires LAST, after all due evaluations — index.ts:3462 uses it for heartbeat writes + expired-run sweeps, which must see this tick's state.
**Invariant:** at most one `due` per automation per epoch-minute even if multiple compiled crons match or runTick is invoked manually twice in the same minute; the ticker NEVER launches anything itself — it only emits to the composition root's single `tryLaunch` funnel.
**Probe:** `packages/server/tests/automation-scheduler.test.ts` — `"never fires twice for the same automation and minute"` (:98 — three manual ticks 10:15:05/10:15:40/10:16:05 ⇒ exactly 2 due), `"tolerates invalid schedules without firing"` (:108), `"emits tick after evaluating automations"` (:120).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "AutomationScheduler runTick lastFiredMinute", limit: 6, detail: "compact" });
// → runTick @ automation-scheduler.ts:36-61 (+ scheduleNextTick/start/dispose)
```

## Verdict
Adopt the alignment-delay + self-rescheduling-unref'd-timeout + epoch-minute dedupe pattern verbatim; adapt the tick interval and alignment constant to host granularity; omit the watch/event trigger exclusion only if your host has no other trigger managers. 10 direct tests pin the contract at this commit.
