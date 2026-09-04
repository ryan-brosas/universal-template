<!-- capsule-v2 -->
# Rank check workflow — how does a run state machine survive batch failures without double-counting or resurrecting superseded runs?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** Where do prepare/finalize re-check terminal status, and why does finalize recount from the DB?

## Prepare / batched checks / finalize with DB-recount
**Path/Symbol:** `src/server/workflows/RankCheckWorkflow.ts:RankCheckWorkflow.runScoped` (:273-391), `prepareRankCheckKeywords` (:52-136), `finalizeRankCheckRun` (:138-227).
**Signature:** `class RankCheckWorkflow extends WorkflowEntrypoint<Env, RankCheckParams>`; steps: `check-active` → `prepare` → per-batch live/queued → `finalize`, catch ⇒ `mark-failed`.
**Data Shape:** Params carry runId/configId/billingCustomer/domain/location/language/devices/serpDepth/trigger (`manual`|`scheduled`)/optional keywordIds subset + maxCostCredits approval.

### Decisive source
```ts
// finalize: If stale-cleanup already marked our run failed, don't overwrite that
// decision with a completed status — a replacement run may already be underway.
const run = await RankTrackingRepository.getRunById(input.runId);
if (!run || run.status === "failed" || run.status === "completed") { /* skip finalization */ }
// Snapshots were written incrementally by each batch step.
// Count from DB to get the authoritative keyword count.
const snapshots = await RankTrackingRepository.getSnapshotsForRun(input.runId);
const keywordsChecked = new Set(snapshots.map((s) => s.trackingKeywordId)).size;
```

**Flow:** prepare re-reads the run and bails via NonRetryableError if no longer active (never resurrect a superseded run) → filters keywordIds subset → estimates credits (queued pricing for scheduled) + verifies Autumn balance → batches write snapshots INCREMENTALLY (partial results survive batch failures) → batch errors are captured as `batchError`, not thrown — finalize still runs → finalize recounts keywords from the snapshot table, writes completed (+ partial-failure errorMessage), sets config.lastCheckedAt, clears lastSkipReason → mark-failed maps INSUFFICIENT_CREDITS to config.lastSkipReason for UI surfacing. Note: nextCheckAt is NOT set here — the cron advances it eagerly before starting the workflow to prevent retry storms.
**Invariant:** A completed/failed run is terminal — every late writer (finalize, mark-failed, prepare) re-checks and defers to stale-cleanup's decision. keywordsChecked is authoritative only from the DB recount (per-batch progress counters are UI hints). Flipping status away from pending/running is what releases the single-flight slot.
**Probe:** `src/server/workflows/RankCheckWorkflow.test.ts` (prepare bail-out on terminal run, finalize recount, partial-failure completion).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "finalizeRankCheckRun prepareRankCheckKeywords snapshots recount", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt incremental snapshot persistence + terminal-status deference in every late writer + DB recount at finalize. Adapt step names/configs and billing gate placement to your engine. Omit PostHog captureServerEvent and Workers-Logs one-line summary formatting.
