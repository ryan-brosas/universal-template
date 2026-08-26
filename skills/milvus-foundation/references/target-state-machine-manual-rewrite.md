<!-- capsule-v2 -->
# Compaction target state machine & manual-rewrite admission — how do declarative targets persist, activate, and refuse invalid scope?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What is the lifecycle of a persisted CompactionTarget record (ACTIVE→INACTIVE), and what does a manual rewrite request have to satisfy before one is created?

## compactionTargetMeta persistence + manualRewriteCompactionTarget factory
**Path/Symbol:** `internal/datacoord/compaction_target.go` (meta 38–215, factory 221–257, runtime target 259–407); `internal/datacoord/compaction_trigger_v2.go:saveManualRewriteCompactionTarget` (370–395).
**Signature:** `func (m *compactionTargetMeta) UpdateCompactionTargetState(ctx, targetID int64, state datapb.TargetState) error`; `func (target *manualRewriteCompactionTarget) Create(ctx, alloc allocator.Allocator) (*datapb.CompactionTarget, error)`; `func evaluateCompactionTargetStateChange(target *datapb.CompactionTarget, state datapb.TargetState) (inactivatedAtTS uint64, changed bool)`.
**Data Shape:** `datapb.CompactionTarget{TargetID, CollectionID, Intent(TargetIntent_INTENT_REWRITE), Properties(map[string]string incl sorted segment ids), ExpectedTS, TailLimit, State, ActivatedAtTS, InactivatedAtTS}`. `finite() = TailLimit >= 0`.

### Decisive source
```go
func (target *manualRewriteCompactionTarget) Create(...) (*datapb.CompactionTarget, error) {
	if target.collectionID <= 0 {
		return nil, merr.WrapErrParameterInvalidMsg("finite compaction target requires a collection scope")
	}
	targetID, activatedAtTS, err := allocCompactionTargetIdentity(ctx, alloc)
	...
	return &datapb.CompactionTarget{
		TargetID: targetID, CollectionID: ...,
		Intent: datapb.TargetIntent_INTENT_REWRITE,
		State:  datapb.TargetState_TARGET_STATE_ACTIVE,
		ActivatedAtTS: activatedAtTS, ...
```
```go
if state == datapb.TargetState_TARGET_STATE_INACTIVE {
    if target != nil && target.GetState() == state && target.GetInactivatedAtTS() != 0 {
        return target.GetInactivatedAtTS(), false // idempotent no-op
    }
    return tsoutil.ComposeTSByTime(time.Now()), true
}
```

**Flow:** Manual rewrite path (plain ManualCompaction when target-based mode enabled): rejects partition/channel filters (collection-scope only), checks collection not compaction-blocked, builds factory with SORTED segment ids, allocates identity (ID + activation timestamp from the SAME allocator pair), persists ACTIVE. Reconciler ticks then drive it (see target-reconciler capsule); satisfaction flips to INACTIVE through UpdateCompactionTargetState which computes inactivation ts via the idempotence table, persists FIRST, mirrors to memory only if loaded. Reload materializes each record through `newCompactionTarget`: unknown intent ⇒ warning + inert runtime wrapper that stays durable but never activates; INTENT_REWRITE with finite scope and zero collection ⇒ validation error surfaced at load.
**Invariant:** Persist-before-memory on every mutation; state transitions are idempotent (unchanged state + already-stamped ts ⇒ changed=false). Activation timestamps come from the timestamp allocator so ExpectedTS ordering is globally consistent — targets only cover data visible at/before their activation. Inert-on-corrupt-load keeps bad rows observable instead of crashing startup.
**Probe:** `internal/datacoord/compaction_target_reconciler_test.go:297 TestCompactionTargetReconcilerWaitsForSnapshotCreatedAfterTarget`, `:332 _KeepsTemporarilyBlockedMatchActive`; direct-source pin: idempotence branch :397–401.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "compactionTargetMeta SaveCompactionTarget manualRewriteCompactionTarget evaluateCompactionTargetStateChange", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt intent-tagged desired-state records with idempotent terminal transitions for declarative maintenance APIs. Adapt Properties encoding to your filter DSL. Omit milvus REST alterConfig interplay. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
