<!-- capsule-v2 -->
# Segment view grouping & channel-partition iteration — how do policies enumerate candidate segments per compaction group without missing cross-channel skew?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What is the canonical helper for "all eligible segments of one collection grouped by partition+channel", and which eligibility predicates compose into it?

## GetSegmentsChanPart + predicate stack
**Path/Symbol:** `internal/datacoord/compaction_policy_clustering.go` usage :147–156 and `compaction_policy_single.go:triggerOneCollection` :278–286; predicate helpers `isSegmentHealthy`/`isFlushed` (`meta.go:2775–2780`, common.go), `GetSegmentsChanPart` (common policy util).
**Signature:** `partSegments := GetSegmentsChanPart(policy.meta, collectionID, SegmentFilterFunc(func(segment *SegmentInfo) bool { ... }))` yielding `[]chanPartSegments{collectionID, partitionID, channelName, segments}`.
**Data Shape:** Standard eligibility conjunction: `isSegmentHealthy && isFlushed && !segment.isCompacting && !segment.GetIsImporting() && level-constraint && !segment.GetIsInvisible() && !policy.meta.isSegmentCompactionProtected(id)`.
**Level constraints differ by policy:** clustering excludes only L0; single requires exactly L2; storage-version excludes L0; manual candidates exclude L0 AND L2 (`isNormalManualCompactionSegment`).

### Decisive source
```go
partSegments := GetSegmentsChanPart(policy.meta, collectionID, SegmentFilterFunc(func(segment *SegmentInfo) bool {
    return isSegmentHealthy(segment) &&
        isFlushed(segment) &&
        !segment.isCompacting && // not compacting now
        !segment.GetIsImporting() && // not importing now
        segment.GetLevel() == datapb.SegmentLevel_L2 && // only support L2 for now
        !segment.GetIsInvisible() &&
        !policy.meta.isSegmentCompactionProtected(segment.GetID()) // not protected by snapshot
}))
```
```go
func isSegmentHealthy(segment *SegmentInfo) bool {
	return segment != nil &&
		segment.GetState() != commonpb.SegmentState_SegmentStateNone &&
		segment.GetState() != commonpb.SegmentState_NotExist &&
		segment.GetState() != commonpb.SegmentState_Dropped
}
```

**Flow:** Policies never hand-roll segment enumeration: they call GetSegmentsChanPart with a policy-specific predicate closure. The helper selects from meta under its lock, groups results into chanPartSegments buckets so downstream logic reasons per compaction group (a group = one partition on one channel = one parallel unit). Optional post-filters refine inside the loop: index-based filtering (`FilterInIndexedSegments` when IndexBasedCompaction), namespace-sort requirements (clustering), all-L2 composition check.
**Invariant:** Health is defined negatively (state ∉ {None, NotExist, Dropped}) — adding states to that set silently changes every policy at once, which is the point. `isCompacting`/`IsImporting` are in-memory flags consulted at TRIGGER time only; admission re-checks via CAS because flags change between trigger and enqueue. Level predicates encode each policy's data-class contract — porting a policy without its exact level constraint breaks the tiering system.
**Probe:** Direct-source pin: single-policy filter :278–286; health def meta.go :2775–2780. Upstream suites exercise grouping through every policy test file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "GetSegmentsChanPart isSegmentHealthy isFlushed SegmentFilterFunc", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt shared enumeration helper + per-policy predicate closures for any multi-tenant maintenance engine. Adapt the flag trio (compacting/importing/invisible) to your lifecycle. Omit milvus level taxonomy beyond L0/L1/L2 mapping guidance. Caveat: cgo-blocked runner; direct source read at pin.
