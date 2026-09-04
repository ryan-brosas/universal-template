<!-- capsule-v2 -->
# Random-plugs ambient workflow — how does an org keep an account "alive" with organic-feeling activity without touching the campaign pipeline?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** what does the always-on plugs workflow do differently from campaign bot-jobs when enqueueing through the SAME per-bot throttler?

## Pick a random plug → enqueue as priority −1 ghost lead → wait for completion → sleep 20–60 min
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.plugs.ts:workflowPlugs` (:29-134); throttler child-boot :41-58; ghost enqueue :94-110; jitter :118-123.
**Signature:** `workflowPlugs({botId, orgId})` — infinite loop; `getPlugs(botId, orgId)` returns configured plug rows (data = JSON settings string); tool description resolved via `getPlugsDescription(platform).find(p => p.identifier === randomPlug.identifier)` → gives `{methodName, url}` for enqueue.
**Data Shape:** enqueue payload mirrors bot-job shape but sets `workflowId: workflowIdInternal + 'ignore'`, `stepId/nodeId/leadId: workflowIdInternal`, `priority: -1`, `totalRepeat: 0`, `ignoreLead: true`.

### Decisive source
```ts
const randomPlug = plugs[Math.floor(Math.random() * plugs.length)];
...
await throttler.signal(enqueue, {
  ..., workflowId: workflowIdInternal + 'ignore',
  priority: -1, ignoreLead: true, ...
});
await condition(() => triggerStepId === workflowIdInternal);
```

**Flow:** ensure the bot's immortal throttler exists (startChild try/catch get-or-create, ABANDON both close and cancel) → each cycle: re-read plug configs from DB, pick ONE uniformly at random, resolve its @Tool descriptor → signal the throttler as a priority −1 item that sorts AHEAD of all real campaign work → block until the throttler answers `stepCompleted(workflowIdInternal)` inside a cancellable scope (cancelAll handler aborts mid-wait) → reset trigger latch → sleep a UNIFORM random 20–60 min → snapshot via continueAsNew after >50 runs.

**Invariant:** priority −1 exploits the sort ladder (`priority asc` first) so ambient activity never queues behind bulk campaigns but still respects the per-bot gap, restrictions, working hours and active/logged gates — the throttler cannot tell "real" from "ambient" except by payload fields. The `'ignore'` suffix on workflowId prevents collision with any campaign workflow id AND marks the step-completion callback route; `ignoreLead:true` suppresses saveActivity so ghost runs never pollute lead history (throttler :370 checks `job.leadId !== 'ignore' && !job.ignoreLead`). Uniform jitter (NOT per-tool delay) is the pacing contract; the 50-run continueAsNew keeps event history bounded independent of queue depth.

**Probe:** deterministic pins from repo root: `grep -cF 'Math.random() * plugs.length' apps/orchestrator/src/workflows/workflow.plugs.ts` → 1; `grep -nF 'min + Math.floor' apps/orchestrator/src/workflows/workflow.plugs.ts` → :121; `grep -cF "workflowIdInternal + 'ignore'" apps/orchestrator/src/workflows/workflow.plugs.ts` → 1; `grep -cF 'runs > 50' apps/orchestrator/src/workflows/workflow.plugs.ts` → 1; `grep -cF 'priority: -1' apps/orchestrator/src/workflows/workflow.plugs.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "workflowPlugs random plug enqueue throttler", limit: 10 });
```

## Verdict
Adopt the ghost-priority enqueue pattern for maintenance activity sharing one account queue with real work; adapt jitter window and run threshold; omit the specific plug catalog. Coverage caveat: deterministic probes only.
