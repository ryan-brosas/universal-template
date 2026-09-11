<!-- capsule-v2 -->
# Queue-retraction signals — how do you retract queued-but-NOT-yet-run jobs when a campaign node or whole workflow is edited/deleted mid-flight?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** jobs already accepted by a per-bot durable queue are now obsolete because their workflow node/row changed or vanished — how are they removed without killing the queue?

## Reverse-index splice handlers + edit/delete emitter fan-out
**Path/Symbol:** signal definitions `apps/orchestrator/src/signals/remove.nodes.from.queue.signal.ts` (:3-5, :7-9); consumers `apps/orchestrator/src/workflows/workflow.throttle.ts` (`removeNodesFromQueueByNodeIdSignal` :148-161, `removeNodesFromQueueByWorkflowIdSignal` :163-176); emitters `shared/server/database/workflows/workflows.service.ts:updateWorkflow` (:261-301) and `:deleteWorkflow` (:303-369).
**Signature:** `defineSignal<[string]>`; handler `async (w: string)` where `w` = one nodeId (edit) or the whole workflowId (delete).
**Data Shape:** queue entries carry BOTH keys: `nodeId` = makeId(1000) minted at enqueue time, `workflowId` = owning campaign id. Repository `updateWorkflow` returns `list.toDelete` (node ids removed by the edit).

### Decisive source
```ts
setHandler(removeNodesFromQueueByNodeIdSignal, async (w) => {
  await lock.runExclusive(async () => {
    const indexes = q.reduce((acc, item, index) => {
      if (item.nodeId === w) acc.push(index);
      return acc;
    }, [] as number[]);
    for (const index of indexes.reverse()) q.splice(index, 1); // descending!
  });
});
```

**Flow:** EDIT: repository update returns `toDelete` → parse each participating bot account from the workflow-graph children JSON → for every RUNNING `userWorkflowThrottler` of those bots, signal the nodeId variant once per deleted node (:279-298). DELETE: first signal the workflowId variant to the literal `enrichment` singleton handle (:318-324), then to every bot throttler (:326-351), THEN terminate all running workflows whose search attribute matches `workflowId="${id}"` with reason 'Workflow deleted' (:353-369).
**Invariant:** splices run DESCENDING under the SAME `Mutex().runExclusive` as `enqueue`, so a concurrent push can never shift an index between collect and splice; retraction only removes not-yet-dispatched work — a job already snapshot-copied to the head (`const job = { ...q[0] }`) still runs; every signal/terminate is individually try/caught, so one dead handle never aborts the fan-out, and DB deletion proceeds even if all signals fail.
**Probe:** no upstream tests exist (zero *.spec/*.test files). Deterministic pins (executed): `grep -n 'removeNodesFromQueueBy' apps/orchestrator/src/workflows/workflow.throttle.ts` → :148/:163; `grep -n "removeNodesFromQueueBy" shared/server/database/workflows/workflows.service.ts` → :293/:321/:341.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", name_pattern: ".*[Rr]emoveNodes.*", limit: 8 });
// → signals/remove.nodes.from.queue.signal.ts :3-5 / :7-9 (BM25 misses bare signal constants; pattern mode is exact)
```

## Verdict
Adopt the retract-by-key signal pair (per-node for edits, per-workflow for deletes) with reverse-index splices under the queue mutex. Adapt key choice to your job identity model. Omit the workflow-graph JSON child-parsing detail (product schema). Coverage caveat: pinned by whole-source reads; graph coverage no_recorded_issue on both files.
