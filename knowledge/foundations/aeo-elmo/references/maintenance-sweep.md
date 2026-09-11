<!-- capsule-v2 -->
# Maintenance self-healing — who restarts a prompt chain that died?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How does a periodic sweep revive dead chains, expedite stalled jobs, and page on real outages — without storming healthy ones?

## Pure decision core + thin executor
**Path/Symbol:** `packages/lib/src/run-policy/maintenance.ts:computeMaintenanceDecisions` (L52–103), `OVERDUE_ALERT_GRACE_MS` (L16), `EXPEDITE_MIN_INTERVAL_MS` (L13), `lastRunQueryWindowMs` (L150–153); executor `apps/worker/src/jobs/schedule-maintenance.ts:runMaintenanceCheck` (L52–245).
**Signature:** `computeMaintenanceDecisions(promptStates: MaintenancePromptState[], now: Date): { toSchedule, toExpedite, alertOverdueCount }`.
**Data Shape:** per prompt: plan (targets+rescheduleHours), lastRunAtByKey (failed runs write NO row), pendingJob `{jobId, state: created|active|retry, consecutiveFailures}` (best state wins: active > retry > created).

### Decisive source
```ts
if (state.plan.targets.length === 0 || state.plan.rescheduleHours === null) continue; // parked: unentitled/no picks
if (isPromptOverdue(state, nowMs, OVERDUE_ALERT_GRACE_MS)) decisions.alertOverdueCount++;
if (state.pendingJob && state.pendingJob.state !== "created") continue;  // running/retrying = handled
const hasAnyRun = state.lastRunAtByKey.size > 0;
const isOverdue = !hasAnyRun || isPromptOverdue(state, nowMs, 0);
```

**Flow:** gather (brands→org entitlements map→prompts→plans per brand in try/catch so one broken brand can't kill the sweep) → one bounded aggregate last-run query → pending-job map via raw SQL over `pgboss.job` → pure decisions → expedite = `UPDATE pgboss.job SET start_after = now() WHERE id IN (...) AND state='created'` (uuid-cast per id because drizzle flattens arrays into one text param); schedule = batched `boss.send` with `singletonKey: prompt-{id}`, singletonSeconds 1h.
**Invariant:** a parked chain is never overdue and never alerted ("a canceled customer is not an outage"). A prompt with zero recorded runs is inherently overdue even if just created. The Sentry error is throttled in-process to once per 30min while an outage persists.
**Probe:** `packages/lib/src/run-policy/maintenance.test.ts` (decision matrix); the composition is proven by scheduling-under-failure.test.ts's simulated-clock harness.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "computeMaintenanceDecisions getPendingJobMap reportOverduePrompts EXPEDITE_MIN_INTERVAL", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the gather→decide(pure)→execute split — it makes self-healing exhaustively unit-testable; adapt the pg-boss specifics if your queue differs; omit the uuid-cast workaround only when your query builder parameterizes arrays correctly.
