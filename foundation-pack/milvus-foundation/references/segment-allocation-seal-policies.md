<!-- capsule-v2 -->
# Segment allocation & seal policy stack — when does an insert land in a growing segment vs a new one, and what flips growing→sealed?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What is the exact row-accounting for allocating inserts to open segments, and which seal policies (segment-level and channel-level) fire in what order?

## AllocatePolicyL1 + policy-object SegmentManager
**Path/Symbol:** `internal/datacoord/segment_allocation_policy.go:AllocatePolicyL1` (lines 60–106), seal policies (121–302); `internal/datacoord/segment_manager.go` (policies :139–233, AllocSegment :307–369, tryToSealSegment :635–690, ExpireAllocations :569–597).
**Signature:** `type AllocatePolicy func(segments []*SegmentInfo, count int64, maxCountPerL1Segment int64, level datapb.SegmentLevel) ([]*Allocation, []*Allocation)`; `func (s *SegmentManager) tryToSealSegment(ctx context.Context, ts Timestamp, channel string) error`.
**Data Shape:** `Allocation{SegmentID, NumOfRows, ExpireTime}` recycled via `sync.Pool`. SegmentManager keeps `channel2Growing`/`channel2Sealed` ConcurrentMap[channel]UniqueSet guarded by `KeyLock[string]` per channel. Seal policies: segment-level `[]SegmentSealPolicy{ShouldSeal(seg,ts)(bool,string)}` and channel-level `[]channelSealPolicy(channel,segs,ts)([]*SegmentInfo,string)`.

### Decisive source
```go
// When inserts are too fast, hardTimeTick may lag, causing segment to be unable
// to seal in time. To prevent allocating large segment, introducing the
// sealProportion factor here. The condition `free < 0` ensures that the
// allocation exceeds the minimum sealable size, preventing segments from
// remaining unsealable indefinitely.
maxRowsWithSealProportion := int64(float64(segment.GetMaxRowNum()) *
    paramtable.Get().DataCoordCfg.SegmentSealProportion.GetAsFloat())
free := maxRowsWithSealProportion - segment.GetNumOfRows() - allocSize
if free < 0 { continue }
free = segment.GetMaxRowNum() - segment.GetNumOfRows() - allocSize
if free < count { continue }
```

**Flow:** AllocSegment: per-channel KeyLock → collect healthy growing segments of that partition (pruning vanished ids inline) → `estimateMaxNumOfRows` from schema (`SegmentMaxSize / estimated size-per-record`, zero-size schema rejected) → `AllocatePolicyL1`: while count ≥ maxPerSegment carve full new segments; then scan existing segments in order — skip if free-by-sealProportion < 0, skip if true-free < count; else attach the whole remainder to the FIRST fitting segment and return; leftover opens a new segment. Every allocation stamped with expireTs = now + SegAssignmentExpiration; `ExpireAllocations` later drops expired allocations so unflushed rows can re-allocate. tryToSealSegment runs SEGMENT policies first (byBinlogFileNumber counts ONLY first field's binlogs :150–156; byLifetime compares ts − startPosition; byCapacity with random jitter ratio; byIdleTime with min-size floor), then CHANNEL policies (sealByTotalGrowingSegmentsSize seals the single largest growing seg over memory threshold; sealByBlockingL0 walks start-pos-sorted growing segs sealing each whose earlier position still overlaps blocking-L0 mass above size/entry limits).
**Invariant:** Allocation accounting must include PENDING allocations (`allocSize`) not just NumOfRows, or concurrent requests double-book a segment. The two-threshold check (sealProportion gate vs hard max) is load-bearing: it prevents allocations that could never be sealed. Channel policies may return multiple seals at once; already-sealed-this-tick ids are skipped via `sealedSegments` map.
**Probe:** `internal/datacoord/segment_allocation_policy_test.go:241 Test_sealByBlockingL0` (constructs L0a/L0b/L0c vs G1..G4 overlap scenario matching the ASCII comment at :252–260), `:207 Test_sealByTotalGrowingSegmentsSize`, `:162 TestSealSegmentPolicy`; `tests/integration/sealpolicies/seal_policies_test.go:43 TestSealPolicies`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "AllocatePolicyL1 tryToSealSegment sealByBlockingL0 channelSealPolicy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pending-inclusive row accounting + policy-stack sealing for any ingest buffer manager. Adapt thresholds/jitter to your storage targets. Omit milvus's streamingnode handoff path (AllocNewGrowingSegment variant). Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
