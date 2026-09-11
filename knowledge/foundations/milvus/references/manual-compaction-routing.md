<!-- capsule-v2 -->
# Manual compaction request routing — how do four mutually exclusive manual modes dispatch through one API surface?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How does ManualCompaction decide between target-rewrite, force-merge, L0, and clustering, and what does each return?

## ManualTrigger flag ladder
**Path/Symbol:** `internal/datacoord/compaction_trigger_v2.go:ManualTrigger` (lines 307–356), `isManualRewriteCompactionRequest`/`isTargetBasedManualRewriteCompactionRequest` (358–368), `saveManualRewriteCompactionTarget` (370–395).
**Signature:** `func (m *CompactionTriggerManager) ManualTrigger(ctx context.Context, req *milvuspb.ManualCompactionRequest) (UniqueID, error)` — returns triggerID.
**Data Shape:** Request flags: `MajorCompaction bool` (clustering), `L0Compaction bool`, `TargetSize int64 MB`. Priority: targetSize ≠ 0 → force-merge; else isL0 → manual L0; else isClustering → clustering; empty flags + target-mode enabled → rewrite-target persistence.

### Decisive source
```go
if isTargetBasedManualRewriteCompactionRequest(req) {
    return m.saveManualRewriteCompactionTarget(ctx, req)
}

events := make(map[CompactionTriggerType][]CompactionView, 0)
if targetSize != 0 {
    views, triggerID, err = m.forceMergePolicy.triggerOneCollection(ctx, collectionID, targetSize)
    events[TriggerTypeForceMerge] = views
} else if isL0 {
    views, triggerID, err = m.l0Policy.triggerOneCollection(ctx, collectionID)
    events[TriggerTypeLevelZeroViewManual] = views
} else if isClustering {
    views, triggerID, err = m.clusteringPolicy.triggerOneCollection(ctx, collectionID, true)
    events[TriggerTypeClustering] = views
}
```

**Flow:** Collection existence/external guards first. Rewrite detection: enabled AND NOT major AND NOT l0 AND targetSize==0 — i.e., a bare request becomes a persisted rewrite TARGET (returns targetID immediately, no plan now). Otherwise each mode calls its policy's triggerOneCollection with manual=true, which bypasses auto-thresholds (clustering skips the interval ladder; L0 uses ForceTriggerAll emitting MULTIPLE plans). Views funnel through the shared notify→Submit* path so manual work obeys the same inspector capacity and admission CAS as automatic compaction. Errors from any branch abort before notify.
**Invariant:** Mode precedence is fixed: explicit targetSize beats flags; bare-request semantics CHANGE when EnableTargetBasedCompaction flips on — callers that previously got force-merge-by-default now get rewrite targets, which is why the hijack is gated on config. All manual modes reuse automatic submission machinery; there is no side-channel queue.
**Probe:** Direct-source pin: flag ladder :337–346; rewrite predicate :358–368. Upstream suite `internal/datacoord/compaction_trigger_v2_test.go` covers manager-level manual flows.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "ManualTrigger saveManualRewriteCompactionTarget TriggerTypeForceMerge", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-entry flag-priority routing over per-mode endpoints for maintenance APIs with overlapping semantics. Adapt flag set to your operations model. Omit milvus REST alterConfig interplay. Caveat: cgo-blocked runner; direct source read at pin.
