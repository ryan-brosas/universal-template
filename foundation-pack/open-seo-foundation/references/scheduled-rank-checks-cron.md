<!-- capsule-v2 -->
# Scheduled rank checks cron — how does a */5 scheduler admit due configs under budget/deadline pressure without ever losing or shifting a schedule slot?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** What are the admission-control rules, the CAS claim protocol, and the error paths that touch (or refuse to touch) nextCheckAt?

## Tick admission control with claim-then-start CAS
**Path/Symbol:** `src/server/features/rank-tracking/services/scheduledRankChecks.ts:runScheduledRankChecks` (:38-256).
**Signature:** `async function runScheduledRankChecks(env: Env): Promise<void>` — cron body wrapped in `withPgClient` at the entrypoint.
**Data Shape:** `SCHEDULED_TASK_UNIT_BUDGET=1000` (units = keywords × devices; DataForSEO cap 2,000 req/min), `TICK_DEADLINE_MS=3min`, `ALREADY_RUNNING_IDS_CAP=20`; per-tick memoized `Map<organizationId, Promise<boolean>>` paid-plan checks.

### Decisive source
```ts
// Never write nextCheckAt on an error: it is the schedule anchor, so
// an error write would permanently shift this config's slot and
// herd-sync configs after an outage. Leaving the row due is the retry.
planCheckErrors++; continue;
// …after beginRankCheckRun returns already_running:
const restored = await RankTrackingRepository.claimDueConfig({
  configId: config.id, projectId: config.projectId,
  observedNextCheckAt: nextCheckAt,      // swap back what we advanced
  nextCheckAt: observedNextCheckAt,      // restore the original anchor
});
```

**Flow:** query due configs (next_check_at ≤ now, oldest first) → per config: projected-stop budget check (`started > 0 && unitsStarted + taskUnits > BUDGET ⇒ break`; FIRST start always admitted so an oversized config can never starve; zero-keyword rows advance with skip reason) → compute next from anchor → claimDueConfig CAS (WHERE next_check_at = observed) writes the ADVANCED schedule + clears/sets lastSkipReason BEFORE starting the workflow → beginRankCheckRun → already_running ⇒ CAS-swap the anchor BACK for the next tick → plan-check/workflow-start errors leave the schedule as written by the successful claim (workflow outage must not make hundreds of configs due again on the next tick). Per-config try/catch so one malformed row can't starve the tick; tick deadline stops early safely (unprocessed configs stay due); function-local plan-check memoization (module scope in Workers = cross-invocation state that would cache a rejection forever).
**Invariant:** nextCheckAt is written ONLY by a successful CAS claim, never as an error side effect. The eager pre-start advancement is what prevents retry storms; restoring it after already_running is what lets a manual trigger land in between.
**Probe:** `src/server/features/rank-tracking/services/scheduledRankChecks.test.ts` (budget admission, skip reasons, restore-on-already-running).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "runScheduledRankChecks claimDueConfig SCHEDULED_TASK_UNIT_BUDGET observedNextCheckAt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: unit-budget admission with first-start exemption, wall-clock tick deadline, claim-before-start CAS on the observed schedule value, and never-write-anchor-on-error. Adapt budget size to your vendor's rate cap. Omit the Workers Logs summary object shape and PostHog correlation fields.
