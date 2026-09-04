<!-- capsule-v2 -->
# Daemon downtime reconciliation — how do I settle what a dead process left behind and what never ran while the machine was off?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** On boot, how do I distinguish "run died mid-flight" from "schedule missed while powered down", without ever launching retroactively?

## Heartbeat gap → enumerateMissedOccurrences → skipped rows
**Path/Symbol:** `packages/server/src/utils/reconcile-downtime.ts:enumerateMissedOccurrences` (14–36) + `packages/server/src/index.ts:reconcileOnStartup` (2811–2842); heartbeat `packages/server/src/heartbeat-store.ts` (strict zod `{version, lastAliveAt}`, tmp+rename).
**Signature:** `enumerateMissedOccurrences(automation: Automation, lastAliveAt: number, now: number): number[]`; `reconcileOnStartup(now: number): void`.
**Data Shape:** returns sorted epoch-ms occurrences (deduped across multi-cron schedules), at most AUTOMATION_DOWNTIME_RECONCILE_CAP = 10 (constants.ts:687), all strictly < now. Lookback floor AUTOMATION_RECONCILE_LOOKBACK_MS = 14 days; minimum outage AUTOMATION_RECONCILE_MIN_DOWNTIME_MS = 90s.

### Decisive source
```ts
// reconcile-downtime.ts:19-21 — the two bounds that stop unbounded walks
const effectiveFrom = Math.max(lastAliveAt, now - AUTOMATION_RECONCILE_LOOKBACK_MS);
...
return memoBy(collected, (epoch) => epoch)
  .sort((a, b) => a - b)
  .slice(-AUTOMATION_DOWNTIME_RECONCILE_CAP);
```

**Flow:** every scheduler tick stamps the heartbeat file (index.ts:3464) — its own file so per-minute writes never rewrite/race the big automations history file. On boot: any run still "launched"/"running" can never resume (the run tracker is in-memory) ⇒ status "missed". Then only if a REAL outage happened (`lastAliveAt !== null && now − lastAliveAt ≥ 90s`) and the automation is enabled+active: walk each compiled cron from `max(lastAliveAt, now−14d)` via `nextCronOccurrence` until `now`, keep the most-recent 10, and append one run record each with `status:"skipped"`, `startedAt:null`, `countsTowardLimit:false`, `trigger:"schedule"`. Skipped runs NEVER launch — they exist so the Triage UI shows what didn't run. No clients exist yet at boot, so nothing broadcasts.
**Invariant:** skipped history never counts toward limits and never triggers execution; sub-threshold gaps (< 90s) are clean restarts that reconstruct nothing; a missing/corrupt heartbeat means first boot ⇒ zero reconstruction; watch/event/webhook triggers have no scheduled occurrences to reconstruct.
**Probe:** `packages/server/tests/reconciliation.test.ts` — `"keeps only the most-recent cap occurrences for a frequent schedule"` (:43 — 60 minutes of every-minute cron collapses to cap=10 ending :59), `"excludes occurrences at exactly now and clamps to the lookback window"` (:72), `"enumerates nothing for a watch trigger"` (:86), integration `"records skipped runs for downtime and downgrades stale launched runs"` (:147), `"treats a sub-threshold gap as a clean restart"` (:181).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "enumerateMissedOccurrences computeNextAutomationRunAt", limit: 5, detail: "compact" });
// → enumerateMissedOccurrences @ reconcile-downtime.ts:14-36 (+ computeNextAutomationRunAt twin for UI next-run display)
```

## Verdict
Adopt the heartbeat + bounded-lookback enumeration + "skipped ≠ launched" ledger verbatim for any long-lived scheduler that survives restarts; adapt the 90s/14d/10-cap constants to host outage profiles; omit the sibling `computeNextAutomationRunAt` (min over compiled crons) unless you also render next-run countdowns. 5 unit + 3 integration tests pin it at this commit.
