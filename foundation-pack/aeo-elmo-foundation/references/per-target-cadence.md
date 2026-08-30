<!-- capsule-v2 -->
# Per-target cadence by history — how do you meter runs without trusting the scheduler?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How can per-target cadence, duplicate-fire immunity, and plan changes all work with one job per prompt?

## Due = history-based, with early-fire tolerance
**Path/Symbol:** `packages/lib/src/run-policy/policy.ts:targetKey` (L184–186), `dueToleranceMs` (L193–195), `isTargetDue` (L197–201), `selectDueTargets` (L238–240), `targetOverdueStatus` (L221–236).
**Signature:** `selectDueTargets(targets: TargetPlan[], lastRunAtByKey: Map<string, Date>, now: Date): TargetPlan[]`; `isTargetDue(plan, lastRunAt?: Date, now): boolean`.
**Data Shape:** `TargetPlan = { config: ModelConfig, intervalHours, replication }`; key = `` `${model}::${provider}::${webSearch ? "web" : "base"}` `` — provider is part of the identity because a brand can track ChatGPT scraped AND grounded-API (same model, same web flag) and keyed on model alone the scraped target's 4/day kept the premium one looking fresh so it never came due.

### Decisive source
```ts
export function dueToleranceMs(intervalHours: number): number {
	return Math.min(30 * 60 * 1000, intervalHours * 3600 * 1000 * 0.25);
}
export function isTargetDue(plan: TargetPlan, lastRunAt: Date | undefined, now: Date): boolean {
	if (!lastRunAt) return true;
	const intervalMs = plan.intervalHours * 3600 * 1000;
	return now.getTime() - lastRunAt.getTime() >= intervalMs - dueToleranceMs(plan.intervalHours);
}
```

**Flow:** every firing resolves the run plan FRESH (entitlements + picks + cadence), fetches last successful run per targetKey within a bounded window (`lastRunQueryWindowMs(maxIntervalHours)`), and fans out only due targets — an expedited/duplicate job re-runs only what is actually stale. Keys are never stored; both sides compute them from columns prompt_runs already records, so changing the key shape costs no migration.
**Invariant:** metering against RECORDED HISTORY (not job cadence) is what makes in-flight pre-upgrade jobs valid and structurally prevents oversampling. "Due" leans EARLY (tolerance up to min(30min, ¼ interval)); the separate `targetOverdueStatus` leans LATE (a whole interval + grace) — one asks "run now?", the other "is something wrong?".
**Probe:** `packages/lib/src/run-policy/policy.test.ts` (due/overdue matrices incl. tolerance edges); maintenance window math pinned by `maintenance.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "targetKey isTargetDue selectDueTargets dueToleranceMs targetOverdueStatus", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt history-metered due-ness + the dual lean-early/lean-late clocks; adapt tolerance constants; omit the entitlements half if self-hosted (unlimited mode collapses to brand cadence × replication).
