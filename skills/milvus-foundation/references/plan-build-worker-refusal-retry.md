<!-- capsule-v2 -->
# Mix compaction plan-build & worker-refusal retry — what exactly goes on the wire to a DataNode, and how does a slot-limited refusal loop back into scheduling?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What does BuildCompactionRequest assemble for a mix/sort plan, and why is CreateTaskOnWorker's failure path a demotion instead of an error?

## Plan assembly + pipelining demotion
**Path/Symbol:** `internal/datacoord/compaction_task_mix.go:BuildCompactionRequest` (lines 347–384), `CreateTaskOnWorker` (83–118); `internal/datacoord/compaction.go:GenerateJSONParams`.
**Signature:** `func (t *mixCompactionTask) BuildCompactionRequest() (*datapb.CompactionPlan, error)`; `func (t *mixCompactionTask) CreateTaskOnWorker(nodeID int64, cluster session.Cluster)`.
**Data Shape:** `datapb.CompactionPlan{PlanID, StartTime, Type, Channel, CollectionTtl, TotalRows, Schema, PreAllocatedSegmentIDs, SlotUsage, JsonParams, SegmentBinlogs[]}`; each binlog entry carries `Deltalogs, IsSorted, Manifest, CommitTimestamp`.

### Decisive source
```go
err = cluster.CreateCompaction(nodeID, plan, t.GetTaskProto().GetCollectionID())
if err != nil {
    // Compaction tasks may be refused by DataNode because of slot limit. In
    // this case, the node id is reset to enable a retry in compaction.checkCompaction().
    // This is tricky, we should remove the reassignment here.
    originNodeID := t.GetTaskProto().GetNodeID()
    ...
    err = t.updateAndSaveTaskMeta(setState(datapb.CompactionTaskState_pipelining), setNodeID(NullNodeID))
    ...
    metrics.DataCoordCompactionTaskNum.WithLabelValues(originNodeID, ..., Executing).Dec()
    metrics.DataCoordCompactionTaskNum.WithLabelValues(NullNodeID, ..., Pending).Inc()
```

**Flow:** Build: nil-schema guard (illegal plan), JSON params generated from schema once, plan skeleton from task proto, then per input segment fetch healthy info — missing ⇒ SegmentNotFound — appending its binlogs/deltalogs/manifest references. Sort tasks additionally price slots by segment size before wiring SlotUsage. Dispatch (`CreateTaskOnWorker`): send to node → refusal ⇒ persist `pipelining`+NullNodeID and flip gauges back to pending so `checkCompaction`'s NeedReAssignNodeID path re-assigns another worker NEXT tick (no inline retry storm); acceptance ⇒ persist `executing`+nodeID. QueryTaskOnWorker then polls results; RPC error/nil ALSO demotes (worker may have restarted losing the plan).
**Invariant:** Worker refusal is a STATE TRANSITION not an exception — the task stays queued forever until some node accepts or it times out. Every dispatch-path state change persists BEFORE gauge updates. The comment "This is tricky" flags that reassignment deliberately happens in checkCompaction, not inline.
**Probe:** `internal/datacoord/compaction_task_mix_test.go:300 TestQueryTaskOnWorker`, `:37 TestBuildCompactionRequest_MixFileResources`, `:163 TestBuildCompactionRequestSchemaVersionGuard`; L0 twin `compaction_task_l0_test.go:199 TestBuildCompactionRequestFailed_AllocFailed`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "mixCompactionTask BuildCompactionRequest CreateTaskOnWorker", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI resolves `selectFlushedSegment Method internal/datacoord/compaction_task_l0.go 304-339` for the L0 twin.)

## Verdict
Adopt refusal-as-demotion with deferred reassignment for any push-to-worker scheduler with per-worker capacity. Adapt plan fields to your wire format. Omit milvus schema-version bump guards unless porting that migration. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
