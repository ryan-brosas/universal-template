<!-- capsule-v2 -->
# L0 delete-compaction eligibility — which delta-log segments may merge with which base segments, and why does the timestamp cutoff matter?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How does the coordinator guarantee an L0 (delete-log) compaction only merges deletes that provably precede every target segment's data, and what happens when no targets exist?

## Position-bounded view grouping + flushed-target selection
**Path/Symbol:** `internal/datacoord/compaction_policy_l0.go:groupL0ViewsByPartChan` (lines 137–161), `internal/datacoord/compaction_task_l0.go:selectFlushedSegment` (lines 304–339) and `BuildCompactionRequest` (341–410).
**Signature:** `func (policy *l0CompactionPolicy) groupL0ViewsByPartChan(collectionID UniqueID, levelZeroSegments []*SegmentView, triggerID UniqueID) []CompactionView`; `func (t *l0CompactionTask) selectFlushedSegment() ([]*SegmentInfo, []*datapb.CompactionSegmentBinlogs, error)`.
**Data Shape:** Views keyed by `"part-chan"` label key. Each `LevelZeroCompactionView` carries `latestDeletePos *msgpb.MsgPosition` seeded from `meta.GetEarliestStartPositionOfGrowingSegments(label)`. Target filter: sealed/flush state, same channel, not importing, level ≠ L0, `segmentEffectiveTs(info) < taskProto.GetPos().GetTimestamp()`.

### Decisive source
```go
// groupL0ViewsByPartChan: only L0 segments whose dmlPos is at or before
// the earliest growing segment's start position are compactable now.
earliestGrowingStartPos := policy.meta.GetEarliestStartPositionOfGrowingSegments(segView.label)
...
// Only choose segments with position less than or equal to the earliest growing segment position
if segView.dmlPos.GetTimestamp() <= l0View.latestDeletePos.GetTimestamp() {
    l0View.Append(segView)
}
```
```go
// selectFlushedSegment: Sealed is unexpected in this selection — fail fast:
if info.GetState() == commonpb.SegmentState_Sealed {
    return nil, nil, merr.WrapErrServiceInternalMsg(
        "L0 compaction selected invalid sealed segment %d", info.GetID())
}
```

**Flow:** Policy filters healthy+flushed+not-compacting+not-importing L0 segments per collection, groups them by partition-channel; each view keeps only segments whose dmlPos ≤ earliest growing start pos (deletes not yet visible to any growing insert must wait). Manual trigger path (`triggerOneCollection`) uses the same grouping. On submit (`SubmitL0ViewToScheduler`, compaction_trigger_v2.go :444–504) the task proto carries `Pos: view.latestDeletePos`. At plan-build time the task re-selects target L1/L2 segments with effectiveTs strictly < Pos; a still-Sealed target is a hard error. Zero targets ⇒ fast-finish plan containing ONLY L0 segments (comment "all data may have been deleted"). Binlog IDs are pre-allocated across ALL input+target segments via `PreAllocateBinlogIDs`.
**Invariant:** An L0 segment is eligible only while its latest delete timestamp precedes the earliest growing-segment start position on its label — merging later deletes into older bases would resurrect deleted rows for in-flight inserts. Targets are re-validated at execution time (positions may have moved since trigger). The Sealed-state fail-fast exists because a sealed-but-unflushed segment can still receive more data after planning.
**Probe:** `internal/datacoord/compaction_task_l0_test.go:161 TestProcessRefreshPlan_SelectZeroSegmentsL0` pins the zero-target fast finish; `:82 _NormalL0` pins normal plan build; `internal/datacoord/compaction_policy_l0_test.go:36 TestL0CompactionPolicySuite` pins view grouping incl. active/idle split.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "l0CompactionPolicy Trigger activeCollections groupL0ViewsByPartChan", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the position-cutoff eligibility rule + fail-fast state re-validation for log-merge-over-base designs (LSM delete compaction). Adapt the timestamp source to your ordering primitive. Omit milvus-specific stats/binlog plumbing. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
