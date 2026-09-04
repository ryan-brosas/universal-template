<!-- capsule-v2 -->
# Launch funnel — how do five trigger kinds share one guarded entry into runs that count (or don't) toward limits?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** Where exactly do finished/disabled guards, limit counting, scheduledFor rounding, and tab opening compose so no trigger path can bypass them?

## tryLaunch / launchAgentRun / onAutomationExit composition
**Path/Symbol:** `packages/server/src/index.ts:tryLaunch` (2708–2790), `launchAgentRun` (2635–2701), `closeRunTabIfRequested` (2793–2803), trigger wiring `:3450-3461`, exit handler `:2214-2225` (SessionManager hook `onAutomationExit` at session-manager.ts:819).
**Signature:** `tryLaunch(automation, trigger): string | null`; `launchAgentRun(automation, trigger): string`; both take the 5-way trigger union `"schedule"|"manual"|"watch"|"event"|"webhook"`.
**Data Shape:** history record `{runId, scheduledFor, startedAt, status: "launched"|"running"|…, countsTowardLimit, findings, changedFiles, unread, log}`; `runTabHandles: Map<runId, handle>` for closeOnFinish.

### Decisive source
```ts
// :2712-2716 — the only gate in the house; manual bypasses BY PASSING HERE
if (trigger !== "manual") {
  const current = automationStore.get(automation.id);
  if (!current || !current.enabled || current.lifecycle === "finished") return null;
}
if (automation.runner.kind === "agent") return launchAgentRun(automation, trigger);
```

**Flow:** four trigger managers (scheduler/folderWatch/sessionEvent/webhook) each emit `due` → ONE `tryLaunch` closure (:3450-3461). Guarded re-read of CURRENT store state (the automation may have changed since the tick snapshot). Shell runners: append "launched" row → count (`counts = trigger !== "manual"`; only this path calls incrementRunCount, which flips lifecycle to "finished" when the budget hits max) → sync watchers/listeners promptly (a watch automation that just hit its limit stops watching now, not next mutation) → build run URL at the LOCAL surface origin (never tailnet — a flapping tailscale serve must not fail the run) with `?run=<id>` → async secret resolution then tab open, remembering the handle for closeOnFinish. Agent runners bypass tabs/PTY entirely: spawn headless, stdout becomes findings, git status becomes changedFiles, straight to "running" so the startup missed-sweep covers restart-mid-run. Completion paths: shell = OSC automation-exit → updateRun completed/failed + redacted log + closeRunTabIfRequested + notifyRunFinished to both event managers; agent = post-run callback that first re-checks `automationStore.get(automation.id)` and DROPS the result if deleted mid-run.
**Invariant:** every launch funnels through tryLaunch — there is no second entry point to forget to guard; manual launches never count and are allowed even on finished/disabled automations (deliberate operator override); `scheduledFor` is floor-to-minute for schedule triggers but raw ms for everything else.
**Probe:** `packages/server/tests/automations-api.test.ts` (1250L suite drives POST /automations/:id/run through these guards); scheduler-side guard pins in `automation-scheduler.test.ts:42-59` (disabled/finished never emit due); tracker handoff in `automation-run-tracker.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "tryLaunch launchAgentRun closeOnFinish", limit: 5, detail: "compact" });
// → index.ts is parse_partial at :3582 — cited ranges verified against raw source; prefer grep over graph spans inside index.ts
```

## Verdict
Adopt the single-funnel + counts-vs-manual split + prompt watcher resync verbatim; adapt surface-origin logic and agent-runner transport to host; omit the CDP tab-handle map if your host has no browser tabs to close. Coverage caveat: index.ts is graph parse_partial (:3582) — ranges here were read from raw source, which is authoritative.
