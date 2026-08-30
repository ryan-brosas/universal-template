<!-- capsule-v2 -->
# Enrichment twin workflow — how does the singleton enrichment queue splice items out mid-flight and keep its provider clocks honest across continueAsNew?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** beyond the failover ladder already mined, what does the enrichment WORKFLOW itself guarantee about identity, cancellation, and history snapshots that a porter would miss?

## Reverse-index splices under mutex; length-equality clock reset; 200-deep snapshot
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.enrichment.ts:workflowEnrichment` (:31-198) — splice helpers :65-78 & :169-174, clock reseed :50-56, snapshot :191-196; signal contract `apps/orchestrator/src/signals/enrichment.signals.ts` (addEnrichment / finishedEnrichment).
**Signature:** items carry `{workflowId, stepId, organizationId, internalWorkflowId, platform, identifier: makeId(10), testedProviders}`; removal signals arrive by workflowId (cancel whole lead's flow) — never by position.
**Data Shape:** `queue` is workflow-local state; every mutation path wraps `mutex.runExclusive`; `identifier` is the stable per-item key used by BOTH the credit-drop splice (:134-142) and post-result splice.

### Decisive source
```ts
setHandler(removeNodesFromQueueByWorkflowIdSignal, async (w) => {
  await mutex.runExclusive(async () => {
    const indexes = queue.reduce((acc, item, index) => {
      if (item.workflowId === w) acc.push(index); return acc;
    }, [] as number[]);
    for (const index of indexes.reverse()) {   // descending ⇒ splices stay valid
      queue.splice(index, 1);
    }
  });
});
...
limitsDelay = !limitsDelay || limitsDelay.length !== enrichmentList.length
  ? enrichmentList.map((p) => ({ name: p.name, delay: Date.now() }))
  : limitsDelay;
```

**Flow:** campaign startChilds the singleton (`workflowId:'enrichment'`, ABANDON parent-close, try/catch = get-or-create) → signals add items with a fresh random `identifier` → main loop picks first item whose untested∩available set is non-empty → on terminal outcome signals the ORIGINATING workflow through `getExternalWorkflowHandle(item.internalWorkflowId).signal(finishedEnrichment, …)` then splices by identifier → snapshot via continueAsNew at empty-or-200 carrying queue + clocks.

**Invariant:** THREE mechanics a porter must not flatten: (1) reverse-order splicing — collecting ascending indexes then iterating `.reverse()` keeps earlier indexes valid while multiple matching items (same workflowId fan-out) are removed in one pass; forward iteration corrupts the array; (2) the provider-clock validity check is LENGTH EQUALITY against the live provider list — adding/removing a provider between restarts silently reseeds ALL cooldowns to now rather than misaligning name→index pairs; (3) the 200 threshold is 4× the throttler's 50 because each item fans out to N providers sequentially inside one loop turn, so event history grows per-provider-attempt, not per-item. The throttler's identical reverse-splice pattern lives at `workflow.throttle.ts:148-176` (nodeId + workflowId variants) — same helper shape duplicated, NOT shared, so porting one does not port the other automatically.

**Probe:** deterministic pins from repo root: `grep -cF 'indexes.reverse()' apps/orchestrator/src/workflows/workflow.enrichment.ts` → 1; `grep -nF 'limitsDelay.length !== enrichmentList.length' apps/orchestrator/src/workflows/workflow.enrichment.ts` → :51; `grep -cF 'identifier: makeId(10)' apps/orchestrator/src/workflows/workflow.enrichment.ts` → 1; `grep -nF 'queue.length === 200' apps/orchestrator/src/workflows/workflow.enrichment.ts` → :191; `grep -cF 'indexes.reverse()' apps/orchestrator/src/workflows/workflow.throttle.ts` → 2 (twin confirmation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "removeNodesFromQueueByWorkflowIdSignal enrichment queue splice", limit: 10 });
```

## Verdict
Adopt reverse-index batch splices under the queue mutex and the length-equality config-change reset; adapt thresholds to your event-history economics; omit nothing behavioral here. Coverage caveat: deterministic probes only.
