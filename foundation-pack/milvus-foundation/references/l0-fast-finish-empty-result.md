<!-- capsule-v2 -->
# L0 fast-finish & empty-result handling — what happens when deletes have nothing to merge into, or when compaction output is empty?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How does the coordinator treat a plan whose targets vanished (all data deleted) without treating it as an error?

## Zero-target fast finish + empty-result tolerance
**Path/Symbol:** `internal/datacoord/compaction_task_l0.go:BuildCompactionRequest` (lines 381–391) and `QueryTaskOnWorker` completed-branch (:131–152); twin `internal/datacoord/compaction_task_mix.go:saveSegmentMeta`.
**Signature:** inside `BuildCompactionRequest`: `if len(flushedSegments) == 0 { return plan, nil }`; result branch `if len(result.GetSegments()) == 0 { mlog.Info("compaction result is empty, all data may have been deleted") }`.
**Data Shape:** Plan returned with `SegmentBinlogs` containing ONLY the L0 segments; no PreAllocatedLogIDs needed.

### Decisive source
```go
flushedSegments, flushedSegBinlogs, err := t.selectFlushedSegment()
if err != nil {
    log.Warn(context.TODO(), "invalid L0 compaction plan, unable to select flushed segments", mlog.Err(err))
    return nil, err
}
if len(flushedSegments) == 0 {
    // Fast finish: no target segments to compact with, return plan with only L0 segments
    log.Info(context.TODO(), "l0Compaction available non-L0 Segments is empty, will fast finish",
        mlog.Any("target position", taskProto.GetPos()))
    return plan, nil
}
```

**Flow:** At plan build: zero eligible targets ⇒ plan ships with only L0 input binlogs and skips PreAllocateBinlogIDs entirely — the worker applies deltas to nothing and reports success trivially. On the result side (`QueryTaskOnWorker`, completed): an empty output segment list logs "all data may have been deleted" and STILL proceeds through ValidateSegmentStateBeforeCompleteCompactionMutation → saveSegmentMeta → meta_saved; empty outputs become zero-row compactTo protos that are immediately state-Dropped in completeMixCompactionMutation (:2625–2627). Both paths end in normal completion metrics.
**Invariant:** "Nothing to do" is success, not failure — treating empty targets/results as errors would wedge delete-only workloads (TTL-expired collections, full-delete partitions) in permanent retry loops. The zero-row→Dropped normalization keeps flushed-segment accounting consistent when outputs vanish.
**Probe:** `internal/datacoord/compaction_task_l0_test.go:161 TestProcessRefreshPlan_SelectZeroSegmentsL0` pins zero-target selection; direct-source pin: fast-finish comment :386–390.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "BuildCompactionRequest selectFlushedSegment fast finish", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI rank-1: `internal.datacoord.selectFlushedSegment Method internal/datacoord/compaction_task_l0.go 304-339`.)

## Verdict
Adopt empty-is-success semantics for maintenance jobs whose inputs may legitimately disappear. Adapt logging levels to your observability norms. Omit milvus's manifest-specific stats shipping. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
