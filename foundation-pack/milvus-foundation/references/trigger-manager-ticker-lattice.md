<!-- capsule-v2 -->
# Trigger manager ticker lattice — how do multiple periodic policies share one inspector capacity without thundering-herd re-planning?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How are six independent compaction policies (L0, clustering, single, storage-version, bump-schema, target) scheduled on separate intervals yet gated by one shared task-slot budget?

## handleTicker gate + policy interface
**Path/Symbol:** `internal/datacoord/compaction_trigger_v2.go:CompactionTriggerManager` (loop 225–275, handleTicker 277–305), `CompactionPolicy` interface (116–124), `notify`/`triggerViewForCompaction` (397–442).
**Signature:** `type CompactionPolicy interface { Enable() bool; Trigger(ctx) (map[CompactionTriggerType][]CompactionView, error); Name() string }`; `func (m *CompactionTriggerManager) handleTicker(ctx context.Context, tickerType TickerType)`.
**Data Shape:** `policies map[TickerType]CompactionPolicy`; six `time.Ticker`s built from distinct params (L0 interval, clustering interval, mix interval ×3 reuse, bump-schema interval). Event map keys: TriggerTypeLevelZeroViewChange/IDLE/Manual, SegmentSizeViewChange, Clustering, Single, Sort, ForceMerge, StorageVersionUpgrade, BumpSchemaVersion.

### Decisive source
```go
if !policy.Enable() {
    return
}
if m.inspector.isFull() {
    mlog.RatedInfo(ctx, rate.Limit(10), "Skip dispatching compaction events since inspector is full",
        mlog.String("policy", policy.Name()))
    return
}
events, err := policy.Trigger(ctx)
```

**Flow:** One goroutine selects over six tickers + stats-task channel (sort compaction is EVENT-driven per segment, not polled). Each fire → handleTicker: policy registered? → enabled? → inspector has free slots? — only then run the expensive view computation (`policy.Trigger`). Returned views go through `notify`: per-view `triggerViewForCompaction` picks Trigger (normal), ForceTrigger (idle L0), or ForceTriggerAll (manual/force-merge); then type-dispatched Submit*ViewToScheduler builds a `datapb.CompactionTask{State:pipelining}` with fresh planID/triggerID and calls `inspector.enqueueCompaction`. ManualTrigger routes by request flags (targetSize→force-merge, l0→manual-L0, major→clustering) with target-based rewrite hijacking plain requests when enabled.
**Invariant:** View COMPUTATION is skipped entirely when slots are full — policies are pure functions of current meta, so skipping-and-retrying next tick loses nothing; this keeps planning cost O(active slots) not O(queued demand). The CompactionTriggerType→CompactionType mapping (:69–86) is total (default Mix). Tickers for storage-version/target intentionally SHARE the mix interval.
**Probe:** Direct-source pin: full-gate comment+RatedInfo :288–292; event-driven sort channel case :261–273. Suite `internal/datacoord/compaction_trigger_v2_test.go:30 TestCompactionTriggerManagerSuite` covers manager behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "handleTicker CompactionTriggerManager notify TriggerTypeLevelZeroViewChange", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt enable→capacity-gate→compute laddering plus event-driven exceptions for multi-policy schedulers. Adapt ticker set to your policies. Omit milvus manual-compaction REST semantics. Caveat: cgo-blocked runner; direct source + upstream suite read at pin.
