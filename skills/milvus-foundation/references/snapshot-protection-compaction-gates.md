<!-- capsule-v2 -->
# Snapshot-protection compaction gates — how do you freeze background rewrites while a consistent read (snapshot/backfill) is in flight?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** At which four points must a compaction pipeline consult snapshot protection, and why is L0 deliberately exempt?

## Four-gate protection lattice
**Path/Symbol:** `internal/datacoord/meta.go:ValidateSegmentStateBeforeCompleteCompactionMutation` (lines 2686–2744); `internal/datacoord/compaction_inspector.go:createCompactTask` admission (:607–618); trigger-level skips in `compaction_policy_single.go:72–76`, `compaction_policy_storage_version.go:121–125`, `compaction_policy_clustering.go:155`, `segment_allocation_policy` consumers; reconciler blocker handling `compaction_target_reconciler.go:99–112`.
**Signature:** `func (m *meta) isCollectionCompactionBlocked(collectionID int64) bool`; `func (m *meta) isSegmentCompactionProtected(segmentID int64) bool`.
**Data Shape:** Two predicates: collection-level (pending snapshot OR unloaded RefIndex) and segment-level (input protected by a live snapshot). Error: `merr.ErrCompactionBlocked`.

### Decisive source
```go
// Snapshot compaction protection exists to keep the sealed-segment list stable
// during backfill — if an L1/L2 segment gets merged away mid-backfill, the
// backfill breaks. L0 segments are transient delete-log carriers, not part of
// that stable list, and L0 compaction only appends deltalogs to L1/L2 targets
// without touching L1/L2 binlogs. So L0 delete compaction is outside the
// protection's concern and must not be blocked.
if t.GetType() != datapb.CompactionType_Level0DeleteCompaction {
    if m.isCollectionCompactionBlocked(t.GetCollectionID()) {
        return merr.WrapErrCompactionBlocked(...)
    }
    for _, segmentID := range t.GetInputSegments() {
        if m.isSegmentCompactionProtected(segmentID) { ... }
    }
}
```

**Flow:** Protection consults happen at (1) TRIGGER time — policies skip blocked collections so no work is even planned; (2) ADMISSION — `createCompactTask` revalidates "so a protection change after planning cannot enter the task queue unchecked"; (3) COMPLETION — ValidateSegmentStateBefore... rejects just before the meta swap; and (4) RECONCILIATION — target matches in blocked collections are skipped for emission but do NOT satisfy targets (`blockedCollections` cache per tick). The L0 exemption appears identically at every gate.
**Invariant:** Checking once is unsound: snapshots can appear between any two stages, so each stage independently re-derives protection state. Exempting L0 is semantically required, not an optimization — L0 merge appends deltalog REFERENCES without rewriting base binlogs, so backfill's stable-segment-list assumption holds. Reconcilers must treat "blocked" as keep-active-not-satisfied or a blocked target would be silently retired.
**Probe:** `internal/datacoord/compaction_target_reconciler_test.go:390 TestCompactionTargetReconcilerPausesAndResumesSnapshotBlockedCollection`, `:332 _KeepsTemporarilyBlockedMatchActive`, `:297 _WaitsForSnapshotCreatedAfterTarget`; direct-source pin: exemption comment :2690–2694.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "isCollectionCompactionBlocked isSegmentCompactionProtected ErrCompactionBlocked", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI resolves the family via `CompleteCompactionMutation ... internal/datacoord/meta.go 2746-2760` adjacency.)

## Verdict
Adopt the four-point revalidation lattice with class-based exemptions for any rewrite pipeline coexisting with consistent reads. Adapt predicate sources to your snapshot registry. Omit milvus RefIndex specifics. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
