<!-- capsule-v2 -->
# Clustering compaction trigger policy — when does data layout justify a full re-cluster, and what makes the result segments sized?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What is the version/interval/size decision ladder for clustering compaction, and how are output row targets derived from observed row width?

## triggerClusteringCompactionPolicy + calculateClusteringCompactionConfig
**Path/Symbol:** `internal/datacoord/compaction_policy_clustering.go:triggerClusteringCompactionPolicy` (lines 277–326), `calculateClusteringCompactionConfig` (225–240), `estimateRowsBySegmentSize` (242–275), `checkAllL2SegmentsContains` gate usage (:163).
**Signature:** `func triggerClusteringCompactionPolicy(ctx, meta *meta, collectionID, partitionID int64, channel string, segments []*SegmentInfo) (bool, error)`; `func estimateRowsBySegmentSize(segments []*SegmentView, expectedSegmentSize int64) (int64, error)`.
**Data Shape:** PartitionStats version record: `{CommitTime int64, SegmentIDs []int64}` from `partitionStatsMeta`. Config: ClusteringCompactionNewDataSizeThreshold, MinInterval, MaxInterval, MaxSegmentSizeRatio, PreferSegmentSizeRatio.

### Decisive source
```go
currentVersion := meta.partitionStatsMeta.GetCurrentPartitionStatsVersion(collectionID, partitionID, channel)
if currentVersion == 0 {
    // never clustered: compact only if new-data mass exceeds threshold
    if newDataSize > Params.DataCoordCfg.ClusteringCompactionNewDataSizeThreshold.GetAsSize() {
        return true, nil
    }
    return false, nil
}
if time.Since(pTime) < Params.DataCoordCfg.ClusteringCompactionMinInterval.GetAsDuration(time.Second) {
    return false, nil // too soon after last clustering
}
if time.Since(pTime) > Params.DataCoordCfg.ClusteringCompactionMaxInterval.GetAsDuration(time.Second) {
    return true, nil  // stale beyond max interval — force
}
// size based on UNCOMPACTED (not in last stats' SegmentIDs) segment mass:
if uncompactedSegmentSize > threshold { return true, nil }
return false, nil
```

**Flow:** Policy requires a clustering key field; one clustering at a time per collection (`collectionIsClusteringCompacting` checks latest trigger's summary state); candidate groups need ALL-L2 composition (`checkAllL2SegmentsContains`) or "performance will fall back" skip. Manual bypasses the ladder. On submit (`SubmitClusteringCompaction` in trigger_v2 :506–572): expected segment size from collection config → `estimateRowsBySegmentSize` derives rows-per-target = expectedSize ÷ observed avg row bytes (totalSize/totalRows across views; zero/negative guards raise) → maxSegmentRows/preferSegmentRows via the two ratios → pre-allocate result segment IDs by total size BEFORE dispatch.
**Invariant:** The interval ladder is ordered min-interval-blocks BEFORE max-interval-forces — inside the window only uncompacted-mass can trigger. Row estimation must divide by OBSERVED row width, never schema-estimated width (schema lies after variable-length fields). Compacted-vs-uncompacted classification is membership in the last partition-stats SegmentIDs list, not any segment flag.
**Probe:** Direct-source pins: currentVersion==0 branch :280–291; min/max interval ordering :300–307; membership-based size split :311–317. Upstream coverage: `internal/datacoord/compaction_policy_clustering_test.go` suite; integration behavior pinned by partition-stats tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "triggerClusteringCompactionPolicy partition stats version estimateRowsBySegmentSize", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI resolves rank-1 `...triggerClusteringCompactionPolicy Function internal/datacoord/compaction_policy_clustering.go 277-326`.)

## Verdict
Adopt the version-aware interval+mass ladder and observed-width row estimation for layout-optimizing rewrites. Adapt "clustering key" to your ordering dimension. Omit milvus analyze-task (vector centroid) plumbing — that lives worker-side. Caveat: cgo-blocked runner; direct source read at pin.
