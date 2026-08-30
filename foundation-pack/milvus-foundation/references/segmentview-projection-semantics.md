<!-- capsule-v2 -->
# SegmentView projection & GetViewsByInfo semantics — what does a coordinator see when it looks at a segment, and where do the L0 row-count lies live?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How is the read-only SegmentView derived from SegmentInfo, and which fields change meaning for L0 segments?

## GetViewsByInfo projection + CompactionGroupLabel keying
**Path/Symbol:** `internal/datacoord/compaction_view.go:GetViewsByInfo` (lines 144–188), `SegmentView` (95–122), `CompactionGroupLabel.Key` (70–93).
**Signature:** `func GetViewsByInfo(segments ...*SegmentInfo) []*SegmentView`; label `Key() = fmt.Sprintf("%d-%s", PartitionID, Channel)`.
**Data Shape:** View fields: ID, label{CollectionID,PartitionID,Channel}, State, Level, startPos/dmlPos, Size/ExpireSize/DeltaSize (float64 bytes), NumOfRows/MaxRowNum, BinlogCount/StatslogCount/DeltalogCount, DeltaRowCount. Source aggregates come from `segment.EnsureStats()`.

### Decisive source
```go
stats := segment.EnsureStats()
numOfRows := segment.GetNumOfRows()
if segment.GetLevel() == datapb.SegmentLevel_L0 {
    // L0 segments record deleted-row count under numOfRows for view
    // purposes (no inserts). DeleteNumRows on Statistics is the
    // persisted equivalent of the legacy CalcDelRowCountFromDeltaLog
    // iteration.
    numOfRows = stats.GetDeleteNumRows()
}
```
```go
// StatslogCount stays on the array path because Statistics has no per-segment
// stat-file count; V3 segments' empty statslogs read as 0 ...
DeltaSize:     float64(stats.GetDeltaBinlogSize()),
DeltalogCount: int(stats.GetDeltaBinlogCount()),
...
StatslogCount: GetBinlogCount(segment.GetStatslogs()),
```

**Flow:** Every policy converts candidates to views ONCE and reasons over cheap immutable snapshots (`Clone` provided; `GetSegmentViewBy` clones per return). Label is the compaction-group identity — partition+channel — used as scheduler exclusion key and L0 view grouping key. Sizes/counters flow from persisted Statistics rather than walking binlogs at trigger time; only StatslogCount still counts array entries because Statistics lacks that field.
**Invariant:** For L0 views, NumOfRows means DELETE rows not insert rows — any consumer computing "total data size" or ratios across mixed-level views must know this or L0 groups inflate by delete counts. Views are projections: mutating them never touches meta; equality (`Equal`) compares metrics only, deliberately excluding positions/state.
**Probe:** Direct-source pin: L0 comment :148–154; V3 statslog comment :170–173. Upstream suite `internal/datacoord/compaction_trigger_v2_test.go:135 TestCompactionViewsExposeTotalSizeAndCollectionTTL` pins total-size/TTL exposure through views.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "GetViewsByInfo SegmentView CompactionGroupLabel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt snapshot-view projection with level-dependent metric semantics for any store where object class changes field meaning. Adapt label tuple to your sharding keys. Omit ExpireSize placeholder. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
