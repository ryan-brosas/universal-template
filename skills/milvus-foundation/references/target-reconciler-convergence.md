<!-- capsule-v2 -->
# Target-based compaction reconciler — how do you converge live data toward a declared desired state with no stored progress?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How does a reconciler decide a compaction target is satisfied, emit bounded work toward it, and stay active through temporary execution blockers?

## Stateless satisfaction predicate + per-tick reconcile
**Path/Symbol:** `internal/datacoord/compaction_target_reconciler.go:Reconcile` (lines 45–90), `compactionViews` (92–133); `internal/datacoord/compaction_target.go:Satisfied` (358–376), `scopeIn` (328–339), `evaluateCompactionTargetStateChange` (396–407).
**Signature:** `func (reconciler *compactionTargetReconciler) Reconcile(ctx context.Context) (map[CompactionTriggerType][]CompactionView, error)`; `func (target *baseCompactionTarget) Satisfied(matches []*SegmentInfo) bool`.
**Data Shape:** Persisted `datapb.CompactionTarget{TargetID, CollectionID, Intent:INTENT_REWRITE, ExpectedTS, TailLimit, State:ACTIVE|INACTIVE, InactivatedAtTS}`; runtime wrapper adds `rule targetRule` + `compactionType`. Satisfaction = per-CompactionGroupLabel match counts all ≤ TailLimit.

### Decisive source
```go
// Satisfaction uses semantic matches before temporary execution
// blockers. A snapshot-protected segment must keep the target active
// until the snapshot releases it.
matches := reconciler.meta.SelectSegments(ctx, target.MatchFilters()...)
if target.Satisfied(matches) {
    satisfiedTargets = append(satisfiedTargets, record)
    continue
}
remaining := maxEvents - len(events[TriggerTypeSingle])
if remaining <= 0 { continue }
events[TriggerTypeSingle] = append(events[TriggerTypeSingle],
    reconciler.compactionViews(ctx, record, target.CompactionType(), matches, remaining)...)
```
```go
// scopeIn: finite targets only cover segments fully visible at ExpectedTS:
if target.finite() && segment.GetDmlPosition().GetTimestamp() > target.GetExpectedTS() {
    return false
}
```

**Flow:** Each tick (TargetTicker, gated by EnableTargetBasedCompaction): fetch ACTIVE targets → for each, select matching segments via semantic filters (collection scope + manual-compaction-segment shape + rule.Match) → Satisfied ⇒ collect for INACTIVE flip; else emit up to `TargetCompactionMaxEvents` MixSegmentView events, skipping segments in blocked collections or index-unreadable (cached blocked-set per collection). After the loop, satisfied targets get persisted INACTIVE via `UpdateCompactionTargetState`, which computes `inactivatedAtTS` and skips unchanged transitions (`evaluateCompactionTargetStateChange`). Reload materializes unknown/intent-less persisted records as inert runtime targets that log warnings but stay durable.
**Invariant:** The target stores NO progress — it is satisfied exactly when no in-scope segment matches its predicate anymore; temporary blockers (snapshot protection) keep it active rather than satisfying it, so the system converges after the blocker clears. Finite targets (TailLimit ≥ 0) never chase data written after ExpectedTS — new inserts are out of scope forever. Emission is bounded per tick but satisfaction is checked BEFORE the bound so capping events cannot delay completion detection.
**Probe:** `internal/datacoord/compaction_target_reconciler_test.go:118 TestCompactionTargetReconcilerLimitsEventsWithoutSkippingSatisfaction`, `:190 _InactivatesRewriteTargetWhenNoMatchRemains`, `:390 _PausesAndResumesSnapshotBlockedCollection`, `:214 _IgnoresDroppedSegmentsForSatisfaction`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "compactionTargetReconciler Reconcile Satisfied", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI rank-1: `internal.datacoord.compactionTargetReconciler Struct ... 16-19`.)

## Verdict
Adopt the stateless-predicate reconciler pattern for declarative maintenance goals (rewrite-to-format, backfill). Adapt MatchFilters/Satisfied to your object model; keep blocker-aware semantics. Omit milvus manual-rewrite CLI plumbing. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
