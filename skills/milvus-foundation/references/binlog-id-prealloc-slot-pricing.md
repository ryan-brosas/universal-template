<!-- capsule-v2 -->
# Binlog ID pre-allocation & slot accounting — how do parallel compaction workers write non-colliding binlog IDs, and how are worker slots priced?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How does the coordinator hand each plan a contiguous ID range big enough for expansion without a second round-trip, and what decides one task's slot cost?

## PreAllocateBinlogIDs + GetTaskSlot lazy pricing
**Path/Symbol:** `internal/datacoord/compaction_util.go:PreAllocateBinlogIDs` (lines 32–69); `internal/datacoord/compaction_task_mix.go:GetTaskSlot` (53–69); `internal/datacoord/compaction_task.go` option `setResultSegments/setTmpSegments`.
**Signature:** `func PreAllocateBinlogIDs(allocator allocator.Allocator, segmentInfos []*SegmentInfo, schema *schemapb.CollectionSchema) (*datapb.IDRange, error)`; `func (t *mixCompactionTask) GetTaskSlot() int64`.
**Data Shape:** Returns `IDRange{Begin, End}`; also back-compat field `plan.BeginLogID = range.Begin` (deprecated but still assigned). Slot cache: `slotUsage atomic.Int64` memoized on first call.

### Decisive source
```go
stats := s.EnsureStats()
binlogNum += stats.GetInsertBinlogCount() + stats.GetDeltaBinlogCount()
for _, l := range s.GetStatslogs() {
    binlogNum += int64(len(l.GetBinlogs()))
}
...
// Compaction output always needs IDs for PK stats (1) and BM25 stats (per BM25
// function). For V3 manifest segments, binlog metadata may be empty since data
// is managed by manifest, but stats output still requires IDs.
minIDsFromSchema := int64(1) // 1 for PK stats
if schema != nil {
    for _, fn := range schema.GetFunctions() {
        if fn.GetType() == schemapb.FunctionType_BM25 { minIDsFromSchema++ }
    }
}
if binlogNum < minIDsFromSchema { binlogNum = minIDsFromSchema }
n := binlogNum * int64(paramtable.Get().DataCoordCfg.CompactionPreAllocateIDExpansionFactor.GetAsInt())
begin, end, err := allocator.AllocN(n)
```
```go
func (t *mixCompactionTask) GetTaskSlot() int64 {
	slotUsage := t.slotUsage.Load()
	if slotUsage == 0 {
		slotUsage = paramtable.Get().DataCoordCfg.MixCompactionSlotUsage.GetAsInt64()
		if t.GetTaskProto().GetType() == datapb.CompactionType_SortCompaction {
			segment := t.meta.GetHealthySegment(ctx, t.GetTaskProto().GetInputSegments()[0])
			if segment != nil {
				slotUsage = calculateStatsTaskSlot(segSize)  // size-proportional
			}
		}
		t.slotUsage.Store(slotUsage)
	}
	return slotUsage
}
```

**Flow:** Plan build sums per-segment insert+delta counts from Statistics plus statslog/BM25 arrays (V2 cumulative arrays; V3 leaves them empty), raises the floor to schema-derived minimums (1 PK-stats + N BM25 functions), multiplies by expansion factor, and allocates ONE contiguous block from the global ID allocator. Workers then split IDs locally — no cross-worker coordination. Slots: mix tasks cost flat config; sort/stats tasks price by input segment size via `calculateStatsTaskSlot`, computed lazily on first scheduler query and memoized in an atomic so repeated ticks don't refetch.
**Invariant:** The expansion factor absorbs under-counting (new deltalog writes during compaction); exhausting a pre-allocated range mid-compaction is unrecoverable for the plan, so over-allocation is the design choice. Schema-minimum exists BECAUSE V3 manifests can report zero binlog files while still emitting stats outputs — counting files alone would under-allocate to zero. Slot memoization must be idempotent: first-call wins even if segment size changed.
**Probe:** `internal/datacoord/compaction_trigger_v2_test.go:117 TestCreateCompactionIDBlockUsesIDExpansionFactor`, `:102 TestCreateCompactionIDBlockRejectsTooLargeBatch`; direct-source pin: min-ID comment :52–55.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "PreAllocateBinlogIDs GetTaskSlot calculateStatsTaskSlot", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI rank-1: `internal.datacoord.PreAllocateBinlogIDs Function internal/datacoord/compaction_util.go 36-69`.)

## Verdict
Adopt range-preallocation-with-expansion-factor for distributed write-ID assignment and size-priced slot admission for heterogeneous task pools. Adapt the minimum-ID floor to your manifest formats. Omit deprecated BeginLogID unless crossing wire versions. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
