<!-- capsule-v2 -->
# Force-merge topology memory budget — how do you size a manual merge-all so it cannot OOM the smallest worker?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** Before merging a whole collection to one target-size segment, how does the coordinator learn real node memory (replicas, embedded nodes, pooling datanodes) and fold it into the plan?

## CollectionTopology query + targetSize validation
**Path/Symbol:** `internal/datacoord/compaction_policy_forcemerge.go:triggerOneCollection` (lines 64–138), `metricsNodeMemoryQuerier.GetCollectionTopology` (176–284), `groupByPartitionChannel` (140–158).
**Signature:** `func (policy *forceMergeCompactionPolicy) triggerOneCollection(ctx, collectionID, targetSize int64) ([]CompactionView, int64, error)`; `func (q *metricsNodeMemoryQuerier) GetCollectionTopology(ctx, collectionID int64) (*CollectionTopology, error)`.
**Data Shape:** `CollectionTopology{CollectionID, NumReplicas, NumShards, IsStandaloneMode, IsPooling bool, QueryNodeMemory map[int64]uint64, DataNodeMemory map[int64]uint64}`. `defaultPoolingDataNodeMemory = 32GB` fallback constant.

### Decisive source
```go
// Convert targetSize from MB to bytes ... Handle overflow: when targetSize is
// very large (e.g., max_int64 for auto-calculate mode)
if targetSize > math.MaxInt64/(1024*1024) {
    targetSizeBytes = math.MaxInt64
} else {
    targetSizeBytes = targetSize * 1024 * 1024
}
configMaxSize := getExpectedSegmentSize(policy.meta, collectionID, collection.Schema)
if targetSizeBytes < configMaxSize {
    return nil, 0, merr.WrapErrParameterInvalidMsg(
        "targetSize %d MB should be greater than or equal to configMaxSize %d MB", ...)
}
```
```go
// Pooling DataNode returns 0 from GetMetrics — use default fallback: 32GB
if infos.HardwareInfos.Memory > 0 {
    dataNodeMemory[nodeID] = infos.HardwareInfos.Memory
} else {
    isPooling = true
    dataNodeMemory[nodeID] = defaultPoolingDataNodeMemory
}
```

**Flow:** Manual compaction with targetSize: blocked-collection guard → collection fetch + triggerID alloc → TTL from properties (failure degrades to 0 with warning, NOT error) → overflow-safe MB→bytes conversion → REJECT target below configured max segment size → select normal-manual-compaction candidates (`isNormalManualCompactionCandidate`: healthy, flushed, not importing, level not L0/L2, shared-selectable, mix-selectable) → live topology query: replicas via GetReplicas; QueryNode memory from QC metrics MINUS embedded QueryNodes inside streaming nodes (filtered by etcd session label `LabelStreamingNodeEmbeddedQueryNode`); DataNode memory per client with pooling-mode 32GB fallback; standalone flag from role → one ForceMergeSegmentView per partition-channel group carrying configMaxSize/expectedTargetSize/topology for downstream bin-packing.
**Invariant:** targetSize is a FLOOR not an exact size — plans may exceed it but never aim below config max. Memory probing must exclude embedded QueryNodes (they share the streamingnode process and double-count) and must tolerate metric-less pooling nodes via explicit default. Topology failure aborts the merge rather than guessing capacity.
**Probe:** Direct-source pins: overflow comment :92–99; embedded-node exclusion :197–215; pooling fallback :254–264. Upstream suite `internal/datacoord/compaction_view_forcemerge_test.go` covers view math incl. topology-driven packing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "forceMergeCompactionPolicy CollectionTopology metricsNodeMemoryQuerier", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI rank-1s: `...CollectionTopology Struct internal/datacoord/compaction_policy_forcemerge.go 28-37`.)

## Verdict
Adopt live-topology-with-fallbacks sizing before any cluster-wide resource-heavy operation. Adapt the exclusion rules to your co-located-process inventory. Omit milvus auto-calculate mode details beyond MaxInt64 handling. Caveat: cgo-blocked runner; direct source + upstream suite read at pin.
