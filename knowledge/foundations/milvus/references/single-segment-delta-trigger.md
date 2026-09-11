<!-- capsule-v2 -->
# Single-segment (delta) compaction trigger — when is one segment worth rewriting purely to shed deletes?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What three independent thresholds declare a single L2 segment "too many deletions", and what guards sort-compaction from re-sorting sorted data?

## hasTooManyDeletions + canTriggerSortCompaction
**Path/Symbol:** `internal/datacoord/compaction_trigger.go:hasTooManyDeletions` (lines 643–682); `internal/datacoord/compaction_policy_single.go:triggerOneCollection` (238–313), `triggerSegmentSortCompaction` (90–159).
**Signature:** `func hasTooManyDeletions(segment *SegmentInfo) bool`; policy filter `GetLevel() == datapb.SegmentLevel_L2` only ("support l2 single segment only for now" :34–36).
**Data Shape:** From `segment.EnsureStats()`: DeltaBinlogCount (file count), DeleteNumRows, DeltaBinlogSize (bytes). Config: SingleCompactionDeltalogMaxNum, SingleCompactionRatioThreshold, SingleCompactionDeltaLogMaxSize; SortCompactionTriggerCount.

### Decisive source
```go
// Too many deltalog files, accumulates IO count.
if deltaLogCount > Params.DataCoordCfg.SingleCompactionDeltalogMaxNum.GetAsInt() { return true }
// The proportion of deleted rows is too large, int64 PK tends to accumulates deleted row counts.
if float64(totalDeletedRows)/float64(segment.GetNumOfRows()) >= Params.DataCoordCfg.SingleCompactionRatioThreshold.GetAsFloat() { return true }
// Delete size is too large, varchar PK tends to accumulates deltalog size.
if totalDeleteLogSize > Params.DataCoordCfg.SingleCompactionDeltaLogMaxSize.GetAsInt64() { return true }
```

**Flow:** Per collection (auto-compaction on, not blocked/external): group flushable L2 segments by channel-partition, optionally index-filter, and emit one MixSegmentView per segment passing hasTooManyDeletions — each view contains ONE segment (mix machinery does the rewrite; "single" refers to input count). Sort path (`triggerSegmentSortCompaction`) fires per-stats-task event: requires EnableSortCompaction, healthy segment, external/blocked/invisible/compacting/importing/snapshot-protected all rejected via `canTriggerSortCompaction`, TTL pulled from collection properties; visible segments capped at SortCompactionTriggerCount while ALL invisible ones pass. Views share one triggerID per tick.
**Invariant:** Three OR'd thresholds target distinct PK-type pathologies by design (row-count for int64 PKs, byte-size for varchar PKs, file-count for IO amplification) — porting only one threshold silently misses two workloads. Zero-row division hazard is avoided because NumOfRows==0 segments fail the ratio float check only after being nonzero elsewhere... in fact the guard is upstream of this call: candidates come pre-filtered as flushed non-empty (flushPolicyL1 requires NumOfRows != 0).
**Probe:** Direct-source pin: threshold comments :649/:659/:670. Upstream suite `internal/datacoord/compaction_policy_single_test.go:34 TestSingleCompactionPolicySuite`; no dedicated hasTooManyDeletions unit at pin (coverage caveat — behavior pinned indirectly through policy tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "singleCompactionPolicy hasTooManyDeletions", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI rank-1: `internal.datacoord.hasTooManyDeletions Function internal/datacoord/compaction_trigger.go 643-682`.)

## Verdict
Adopt the triple-threshold delete-pressure test for LSM-style single-sstable compactions. Adapt thresholds per PK/value type distribution. Omit milvus namespace-sort variants. Caveat: cgo-blocked runner; direct source + upstream suite read at pin.
