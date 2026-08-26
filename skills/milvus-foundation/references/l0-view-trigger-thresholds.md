<!-- capsule-v2 -->
# L0 view trigger thresholds — when do accumulated delta logs justify a merge, and how are picks bounded?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What is the exact min/max threshold ladder that decides whether a group of L0 segments triggers compaction now, and how does the picker stay under the IO ceiling?

## minCountSizeTrigger + pickByMaxCountSize
**Path/Symbol:** `internal/datacoord/compaction_l0_view.go:minCountSizeTrigger` (lines 190–216), `forceTrigger` (220–229), `pickByMaxCountSize` (231–247), `resolveLatestDeletePos` (15–32).
**Signature:** `func (v *LevelZeroCompactionView) minCountSizeTrigger(segments []*SegmentView) (picked []*SegmentView, reason string)`; `func pickByMaxCountSize(segments []*SegmentView, maxSize float64, maxCount int) (picked []*SegmentView, pickedSize float64, pickedCount int)`.
**Data Shape:** Per-segment-view metrics: `DeltalogCount int`, `DeltaSize float64` (populated from Statistics in `GetViewsByInfo`). Config: LevelZeroCompactionTriggerMinSize/MaxSize (floats), TriggerDeltalogMinNum/MaxNum (ints).

### Decisive source
```go
// count >= minDeltaCount OR size >= minDeltaSize triggers a pick bounded by max:
if lo.SumBy(segments, func(view *SegmentView) int { return view.DeltalogCount }) >= minDeltaCount {
    picked, pickedSize, pickedCount = pickByMaxCountSize(segments, maxDeltaSize, maxDeltaCount)
    ...
}

func pickByMaxCountSize(segments []*SegmentView, maxSize float64, maxCount int) (...) {
	idx := 0
	for _, view := range segments {
		targetCount := view.DeltalogCount + pickedCount
		targetSize := view.DeltaSize + pickedSize
		if (pickedCount != 0 && pickedSize != float64(0)) && (targetSize > maxSize || targetCount > maxCount) {
			break
		}
		pickedCount = targetCount
		pickedSize = targetSize
		idx += 1
	}
	return segments[:idx], pickedSize, pickedCount
}
```

**Flow:** `Trigger()` finds the max-dmlPos L0 segment and calls `minCountSizeTrigger`: if total deltalog count ≥ min OR total delta size ≥ min → greedy-pick sorted-by-dmlPos segments while cumulative count/size stay ≤ max bounds. Below both minimums → no trigger unless `ForceTrigger` (idle/manual path) which skips the min check but STILL applies the same max-bound picker. `ForceTriggerAll` loops multi-round: pick, emit round view, remove picked IDs from remaining, repeat until nothing fits. Every emitted view's `latestDeletePos` passes through `resolveLatestDeletePos`, which under `levelzero.forceSelectAllSegments` returns Timestamp=MaxUint64 so ALL L1/L2 targets pass the cutoff filter — a repair mode for import-corrupted StartPosition metadata.
**Invariant:** The first segment is ALWAYS taken even if it alone exceeds max bounds (`pickedCount != 0 && pickedSize != 0` guard) — a plan can violate the ceiling only by one segment, never zero work on a triggered view. Picker input must be dmlPos-sorted (both ForceTrigger paths sort first). Idempotence comment (:35–39): same segment set ⇒ same plan.
**Probe:** Direct-source pin: greedy guard line :238; min-or-size ladder :202/:209. Upstream behavior suite `TestL0CompactionPolicySuite` covers policy-level emission; view-level thresholds are exercised indirectly (no dedicated unit file for pickByMaxCountSize at this pin — coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "LevelZeroCompactionView minCountSizeTrigger ForceTrigger pickByMaxCountSize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt min-threshold-to-act / max-ceiling-per-batch greedy picking for batched maintenance work. Adapt metrics to your cost units. Omit the force-select-all repair mode unless you inherit milvus import bugs. Caveat: cgo-blocked runner; direct source read at pin.
