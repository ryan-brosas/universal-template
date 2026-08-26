<!-- capsule-v2 -->
# Failure backoff — what does a broken provider cost you?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How should a paid recurring job back off when a whole cycle fails, without an outage costing more than normal operation?

## Ramp capped AT the cadence
**Path/Symbol:** `packages/lib/src/run-backoff.ts:FAILURE_BACKOFF_HOURS` (L13), `failureBackoffHours` (L28–32).
**Signature:** `failureBackoffHours(consecutiveFailures: number, cadenceHours: number): number`.
**Data Shape:** ramp `[0.25, 0.5, 1, 2, 4, 8]` hours; `consecutiveFailures` counts failed cycles INCLUDING the one just finished (first failure → index 0); ≤0 or beyond the ramp → cadence; each step is `min(step, cadence)`.

### Decisive source
```ts
export function failureBackoffHours(consecutiveFailures: number, cadenceHours: number): number {
	if (consecutiveFailures <= 0) return cadenceHours;
	if (consecutiveFailures > FAILURE_BACKOFF_HOURS.length) return cadenceHours;
	return Math.min(FAILURE_BACKOFF_HOURS[consecutiveFailures - 1], cadenceHours);
}
```

**Flow:** the cycle handler computes `failedCycles = runPromises.length > 0 && successCount === 0 ? consecutiveFailures + 1 : 0` — ANY successful run clears the streak — and schedules the next attempt at `failureBackoffHours(failedCycles, plan.rescheduleHours)`. The comment states the economics: providers bill on submission/completion, so "anything shorter [than cadence] would mean an outage is billed at a higher rate than normal operation, which is the wrong way round".
**Invariant:** a permanently broken target must converge to exactly its healthy cost. Backoff state rides ON THE JOB payload (`consecutiveFailures` in ProcessPromptData) so it survives with the scheduled next attempt and lets maintenance distinguish "deliberately delayed" from "stalled".
**Probe:** `packages/lib/src/run-backoff.test.ts` (6 cases: settles at cadence after ramp; never exceeds cadence; never faster than shortest step). `packages/lib/src/scheduling-under-failure.test.ts` drives both scheduler decisions over simulated days: day-0 attempts ≤ 8, then `[1,1,1]` per day for a dead provider, gaps ≥ 0.25h forever.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "failureBackoffHours FAILURE_BACKOFF_HOURS scheduleNextRun", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ramp-capped-at-cadence function and the streak-on-job-payload pattern as-is; adapt step values to your billing granularity; omit nothing — the test suite encodes three real incident post-mortems (5-minute refire storm, hourly partial guard, catch-up burst after recovery).
