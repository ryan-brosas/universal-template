<!-- capsule-v2 -->
# Run lifecycle guards — how do you guarantee at most one active run per config without a lock table?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** How does a trigger learn "already running" and how does a stale zombie run get cleared safely?

## Partial-unique-index single flight + workflow-status reconciliation
**Path/Symbol:** `src/server/features/rank-tracking/services/rankCheckRunGuards.ts:beginRankCheckRun` (:140-232), `failRunIfActive` (:120-138), `reconcileActiveRankCheckRun` (:234-250).
**Signature:** `async function beginRankCheckRun(input): Promise<RankCheckTriggerResult>` where result is `{ ok: true; runId } | { ok: false; reason: "already_running"; blockingRunId }`.
**Data Shape:** Coordination model (from the file's own header comment): workflow id === run id; a partial unique index on `rank_check_runs(config_id) WHERE status IN ('pending','running')` enforces ≤1 active run at the DB level; flipping status to completed/failed frees the slot.

### Decisive source
```ts
// At most two attempts: once normally, once after clearing a stale blocker.
for (let attempt = 0; attempt < 2; attempt++) {
  const runId = crypto.randomUUID();
  const created = await RankTrackingRepository.tryCreateRun({ id: runId, /* … */ });
  if (created) { /* workflow.create({ id: runId, … }); on failure: failRunIfActive + terminate */ }
  // INSERT was blocked by the partial unique index — another active run exists.
  const blocker = await RankTrackingRepository.getActiveRunForConfig(input.config.id);
  if (!blocker) continue;              // raced: status flipped between insert and select — loop
  if (attempt === 0) {
    const staleReason = await getStaleRankCheckRunReason({ run: blocker, runId: blocker.id, ageMs: Date.now() - new Date(blocker.startedAt).getTime() });
    if (staleReason) {
      await failRunIfActive(blocker.id, staleReason, blocker);
      continue;                        // slot is free now — retry insert
    }
  }
  return { ok: false, reason: "already_running", blockingRunId: blocker.id };
}
```

**Flow:** tryCreateRun (INSERT hits the partial index) → created ⇒ start Workflow with id=runId (start failure ⇒ failRunIfActive to release the slot, best-effort terminate of the zombie instance, rethrow) → blocked ⇒ inspect the blocking run: workflow-status check (`ACTIVE_WORKFLOW_STATUSES` = queued/running/waiting/waitingForPause/paused) with a 60s startup grace for missing/unknown status → stale ⇒ fail the blocker and retry insert once → genuinely active ⇒ `already_running`.
**Invariant:** A failed INSERT *is* the "already running" signal — no separate lock table. Staleness is only ever mutated by the NEXT begin attempt or an explicit reconcile read (`reconcileActiveRankCheckRun` returns the reason; the READ PATH NEVER MUTATES — mutating from getLatestRun caused a race where the original workflow kept running while a replacement started). `failRunIfActive` is idempotent (no-op on completed/failed).
**Probe:** `src/server/features/rank-tracking/services/RankTrackingService.management.test.ts` (trigger/already-running/stale-reconciliation behaviors).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "beginRankCheckRun failRunIfActive stale blocker partial unique index", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the failed-insert-as-signal pattern, the two-attempt stale-clear loop, read-path reconciliation that reports-but-doesn't-mutate, and idempotent failRunIfActive. Adapt the workflow-status probe (60s grace window values, status enum) to your scheduler. Omit the Cloudflare-specific `env.RANK_CHECK_WORKFLOW.get(id).status()` shape in favor of your engine's equivalent.
