<!-- capsule-v2 -->
# Live vs queued check paths — how does a rank check use the cheap queue without ever losing or duplicating paid work?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** What are the batch sizes, poll cadence, and failure routing for live vs task-queue SERP checks?

## Batched live ladder + queued post/poll/fallback ladder
**Path/Symbol:** `src/server/workflows/rankCheckPaths.ts:runLiveCheck` (:127-151), `runQueuedCheck` (:273-390), `collectQueuedRound` (:195-251), `checkBatchLive` (:82-119).
**Signature:** `runQueuedCheck(step, ctx): Promise<QueuedCheckStats>` where stats = `{ queueTasks, queueCollected, fallbackTasks, fallbackChecked }` in keyword/device task units.
**Data Shape:** Constants: `KEYWORDS_PER_BATCH=10` (live batch), `MAX_TASKS_PER_POST=100` (queued post chunk), poll intervals 4/2/2/2/2/3 minutes (~15-min window), `TASK_GET_CONCURRENCY=25`, `TASK_GETS_PER_COLLECT=500`.

### Decisive source
```ts
// A failed chunk must not abort the run — earlier chunks were already charged at
// DataForSEO, so their results have to be collected. The failed chunk's pairs go
// to the live fallback instead.
} catch (error) { console.warn(…); fallback.push(...chunk); continue; }
pending.push(...posted);
if (posted.length < chunk.length) {          // per-entry rejections
  const acceptedKeys = new Set(posted.map((t) => `${t.keywordId}:${t.device}`));
  fallback.push(...chunk.filter((t) => !acceptedKeys.has(`${t.keywordId}:${t.device}`)));
}
```

**Flow:** expand keywords × devices into one task input per pair → LIVE path: batches of 10 pairs via `Promise.allSettled` (failed calls logged and skipped — metered client already decided each call), snapshot insert + progress update per batch step → QUEUED path: post ≤100-task chunks (each a single metered charge covering the batch); rejected entries and whole failed chunks route to fallback; then rounds of `step.sleep` → free task_get collection at concurrency 25 capped 500/round; completed snapshots persist incrementally (`onConflictDoNothing` makes retries safe/free); transient task_get failures stay pending; after the window, ALL stragglers ([…fallback, …pending]) get ONE live-fallback shot in 10-keyword batches.
**Invariant:** A paid-for posted task is never abandoned — collect failures leave that round pending rather than failing the run ("the posted tasks are already paid for"). Stragglers are double-billed by design (queued post cost + one live call, fractions of a cent). Live-batch per-call failures are skipped not retried because billing was already decided per call.
**Probe:** `src/server/features/rank-tracking/services/scheduledRankChecks.test.ts` (scheduled-path admission + queue stats plumbing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "runQueuedCheck QUEUED_POLL_INTERVALS fallback stragglers", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-ladder structure (cheap async queue with bounded polling, instant-but-pricier live path) and the never-abort-paid-work routing. Adapt poll cadence/concurrency caps to your vendor's SLAs. Omit the DataForSEO-specific tag echo (`keywordId:device`) if your vendor returns correlation ids differently.
