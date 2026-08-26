<!-- capsule-v2 -->
# Compaction trigger ID allocation & view events — why does every trigger allocate a fresh ID before building views, and how do idle vs active views differ downstream?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What is the triggerID's role in dedup/trace, and what distinguishes the three L0 trigger event types?

## Alloc-per-trigger + L0 event typing
**Path/Symbol:** `internal/datacoord/compaction_policy_l0.go:Trigger` (lines 51–102); `internal/datacoord/compaction_trigger_v2.go` type constants (43–66), `triggerViewForCompaction` (397–412), `SubmitL0ViewToScheduler` (444–504).
**Signature:** `newTriggerID, err := policy.allocator.AllocID(ctx)` before grouping views; `events map[CompactionTriggerType][]CompactionView`.
**Data Shape:** TriggerTypes 1–10 (LevelZeroViewChange/IDLE/Manual, SegmentSizeViewChange, Clustering, Single, Sort, ForceMerge, StorageVersionUpgrade, BumpSchemaVersion). Each carries `GetCompactionType()` mapping.

### Decisive source
```go
case TriggerTypeLevelZeroViewIDLE:
    view, reason := view.ForceTrigger()
    return []CompactionView{view}, reason
case TriggerTypeLevelZeroViewManual, TriggerTypeForceMerge:
    return view.ForceTriggerAll()
default:
    outView, reason := view.Trigger()
    return []CompactionView{outView}, reason
}
```
```go
// l0 policy Trigger:
if len(activeL0Views) > 0 {
    events[TriggerTypeLevelZeroViewChange] = activeL0Views
}
if len(idleL0Views) > 0 {
    events[TriggerTypeLevelZeroViewIDLE] = idleL0Views
}
```

**Flow:** Every policy tick allocates ONE fresh triggerID from the global allocator BEFORE grouping — the id stamps all tasks of that round so status queries (`GetCompactionTasksByTriggerID`) and clustering's single-flight check can reason per-round. Views then emit into typed event buckets; notify() dispatches per bucket: ViewChange → normal min-threshold Trigger; ViewIDLE → ForceTrigger (skips minimums, keeps max bounds, one plan); Manual/ForceMerge → ForceTriggerAll (multi-round plans covering ALL segments). SubmitL0ViewToScheduler allocates the task's PlanID separately and embeds the view's latestDeletePos as Pos.
**Invariant:** triggerID uniqueness is what makes "one clustering at a time" checkable via latest-trigger summary and gives every user-facing compaction a stable handle. The same CompactionView object must behave differently per event type through the dispatcher — never bake force semantics into the policy, or manual and automatic paths diverge.
**Probe:** Direct-source pin: dispatch table :400–411. Upstream suites: `TestL0CompactionPolicySuite` (active/idle emission), `compaction_trigger_v2_test.go` manager flows.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "TriggerTypeLevelZeroViewChange triggerViewForCompaction SubmitL0ViewToScheduler", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fresh-round-ID + typed-event-bucket dispatch for any multi-policy maintenance framework with manual overrides. Adapt event vocabulary to your policies. Omit milvus proto plumbing. Caveat: cgo-blocked runner; direct source + upstream suites read at pin.
