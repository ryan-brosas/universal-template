<!-- capsule-v2 -->
# Compaction completion meta mutation — in what order must new segments be published and old ones retired so a crash never loses data?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How does the coordinator swap compacted-from → compacted-to segment metadata atomically, and what re-validations guard against races with collection drop or snapshot protection?

## completeMixCompactionMutation ordering + validation sandwich
**Path/Symbol:** `internal/datacoord/meta.go:completeMixCompactionMutation` (lines 2541–2684), `CompleteCompactionMutation` dispatch (2746–2760), `ValidateSegmentStateBeforeCompleteCompactionMutation` (2686–2744).
**Signature:** `func (m *meta) CompleteCompactionMutation(ctx, t *datapb.CompactionTask, result *datapb.CompactionPlanResult) ([]*SegmentInfo, *segMetricMutation, error)`; called under `m.segMu.Lock()`.
**Data Shape:** Returns `(newSegments []*SegmentInfo, metricMutation *segMetricMutation, err)`. Actions list: `[]metastore.UpdateAction` mixing `AddSegment` (new) then `AlterSegment` (retire inputs). Output proto fields of note: `CreatedByCompaction:true`, `Compacted` on inputs, `DroppedAt` timestamp, `Level:L1`, zeroed `CommitTimestamp`.

### Decisive source
```go
// Add the compactTo segments before marking the compactFrom segments
// dropped, so a crash on the ordered-fallback path always leaves the new
// segments published before the old ones are retired (no data loss).
actions := make([]metastore.UpdateAction, 0, len(compactToInfos)+len(compactFromInfos))
for _, seg := range compactToInfos {
    actions = append(actions, metastore.AddSegment(seg))
}
for _, seg := range compactFromInfos {
    // AlterSegment retires the input using the legacy AlterSegments
    // encoding ... preserves GC-compat binlog write rather than assuming it.
    actions = append(actions, metastore.AlterSegment(seg))
}
if err := m.catalog.Update(m.ctx, actions...); err != nil {
    return nil, nil, err
}
```

**Flow:** (1) For each input segment: fetch from memory; missing ⇒ SegmentNotFound; UNHEALTHY ⇒ "input segment was dropped during compaction mutation" — an explicit re-validation because drop-collection can race between the earlier task-level check and here (:2554–2562). Clone, stamp `DroppedAt`+`Compacted`, prepare Dropped metrics. (2) Schema-nil guard. (3) Fallback positions computed from inputs (`getCompactionFallbackPositions`) then per output segment: recalc start/dml positions from its insert logs; build Flushed L1 proto inheriting partition/channel/maxRowNum from input[0], `LastExpireTime` from task StartTime, stats shipped by compactor NOT recomputed; zero-row outputs immediately marked Dropped. (4) ONE catalog.Update applies add-new-then-retire-old. (5) Only after success: in-memory map updates + caller does `metricMutation.commit()` AFTER successful meta update (compaction_task_mix.go :228–234). Pre-check variant `ValidateSegmentStateBeforeCompleteCompactionMutation` additionally enforces snapshot protection: blocked collections and protected segments reject compaction EXCEPT L0 type, which is deliberately outside snapshot concern (:2690–2694 comment).
**Invariant:** Publish-before-retire inside one transactional action list — reversing AddSegment/AlterSegment order turns any mid-crash into data loss. Metrics commit strictly after meta persistence so gauges never claim work that failed to persist. Admission re-validates at enqueue (`createCompactTask` :607–618 "Revalidate input and snapshot state at admission") AND at completion — neither alone closes the race window.
**Probe:** `internal/datacoord/compaction_task_mix_test.go:74 TestBuildCompactionRequest_MixFileResources`, `:138 TestProcessRefreshPlan_MixSegmentNotFound`; direct-source pin: ordering comment :2653–2655.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "completeMixCompactionMutation ValidateSegmentStateBeforeCompleteCompactionMutation", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI form resolves rank-1 `internal.datacoord.completeMixCompactionMutation Method internal/datacoord/meta.go 2541-2684`.)

## Verdict
Adopt publish-before-retire + dual-point re-validation for any destructive background rewrite of referenced artifacts. Adapt the metastore action abstraction to your transaction API. Omit milvus binlog/GC-compat encoding details. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
