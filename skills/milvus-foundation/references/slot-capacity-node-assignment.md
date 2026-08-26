<!-- capsule-v2 -->
# Compaction task slot capacity & node assignment — how does the coordinator match task slot demand to worker supply across scheduling ticks?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How do pipelining tasks acquire node IDs, and how does the queue capacity interact with per-node slot budgets?

## NeedReAssignNodeID ladder + inspector isFull
**Path/Symbol:** `internal/datacoord/compaction_task_mix.go:NeedReAssignNodeID` (lines 277–279), L0 twin (:292–294 with `hasAssignedWorker` :416–418); `internal/datacoord/compaction_inspector.go:isFull` (699–701) and `loadMeta` re-assignment branch (339–356); `maxCompactionTaskExecutionDuration` (44–50).
**Signature:** `func (t *mixCompactionTask) NeedReAssignNodeID() bool`; `func (c *compactionInspector) isFull() bool { return c.queueTasks.Len() >= c.queueTasks.capacity }`.
**Data Shape:** NullNodeID sentinel vs 0; state must be `pipelining`. Slot usage per type from config (`MixCompactionSlotUsage`) or size-priced for sort/stats tasks; scheduler side (`internal/datacoord/task` GlobalScheduler) consumes GetTaskSlot against node free slots.

### Decisive source
```go
func (t *mixCompactionTask) NeedReAssignNodeID() bool {
	return t.GetTaskProto().GetState() == datapb.CompactionTaskState_pipelining &&
		(t.GetTaskProto().GetNodeID() == 0 || t.GetTaskProto().GetNodeID() == NullNodeID)
}
```
```go
// loadMeta restart path:
if t.NeedReAssignNodeID() {
    if err = c.submitTask(t); err != nil {
        // ignore the drop error
        c.meta.DropCompactionTask(context.Background(), task)
        continue
    }
} else {
    c.restoreTask(t)
}
```

**Flow:** Tasks enter with NodeID unset (pipelining). Each checkCompaction tick, the global scheduler assigns a node whose free slots ≥ task.GetTaskSlot(); assignment persists via SetNodeID then CreateTaskOnWorker fires. Refusal/query-loss demotes back (see plan-build capsule). Restart path (`loadMeta`): persisted pipelining-without-node ⇒ resubmit through the QUEUE (re-prioritized, capacity-checked — enqueue failure drops the meta row as "try best"); already-executing ⇒ restored directly into executingTasks bypassing the queue. Queue capacity bounds PENDING demand only; executing concurrency is governed by per-node slot accounting in the task scheduler.
**Invariant:** NodeID=0 and NullNodeID are distinct sentinel values that BOTH mean unassigned but arise from different paths (fresh vs demoted) — the predicate must accept both or demoted tasks strand forever. Capacity-full enqueue failure during RECOVERY deletes the row rather than wedging startup; the trigger will regenerate equivalent work.
**Probe:** Direct-source pins: dual-sentinel predicate :278; recovery branch :339–356. Upstream suites: `compaction_task_mix_test.go`, `compaction_inspector_test.go` cover both paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "NeedReAssignNodeID hasAssignedWorker restoreTask submitTask", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-sentinel unassigned detection plus queue-vs-direct restore split for recoverable worker pools. Adapt slot pricing to your resource model. Omit milvus's specific slot constants. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
