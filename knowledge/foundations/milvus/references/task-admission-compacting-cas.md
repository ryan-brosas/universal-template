<!-- capsule-v2 -->
# Compaction task admission — how do you guarantee one segment participates in at most one compaction at a time?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What is the check-and-set protocol that turns "segment is compacting" into a loud conflict instead of silent double-booking?

## CheckAndSetSegmentsCompacting + typed failure fan-in
**Path/Symbol:** `internal/datacoord/compaction_inspector.go:createCompactTask` (lines 593–620) and `enqueueCompaction` (556–590).
**Signature:** `func (c *compactionInspector) createCompactTask(t *datapb.CompactionTask) (CompactionTask, error)`; `exist, succeed := c.meta.CheckAndSetSegmentsCompacting(ctx, t.GetInputSegments())`.
**Data Shape:** `(exist bool, succeed bool)` pair: exist=false ⇒ segment gone; succeed=false ⇒ CAS lost. Errors: `merr.ErrCompactionPlanConflict` ("segment is compacting") is a NORMAL, rate-limited log path; anything else warns.

### Decisive source
```go
// Revalidate input and snapshot state at admission so a protection change
// after planning cannot enter the task queue unchecked.
if err := c.meta.ValidateSegmentStateBeforeCompleteCompactionMutation(t); err != nil {
    return nil, err
}
exist, succeed := c.meta.CheckAndSetSegmentsCompacting(context.TODO(), t.GetInputSegments())
if !exist {
    return nil, merr.WrapErrIllegalCompactionPlan("segment not exist")
}
if !succeed {
    return nil, merr.WrapErrCompactionPlanConflict("segment is compacting")
}
```

**Flow:** enqueueCompaction: build the concrete task object by TYPE (mix/L0/clustering/bump-schema constructors), run admission validation, then atomically set compacting flags on ALL inputs — any failure path unwinds with `SetSegmentsCompacting(..., false)` BEFORE returning (timestamp-alloc failure :571, meta-save failure :579, submit failure :585). Conflict errors from triggers are expected churn and logged at rate 60/s; success persists task meta then submits to the queue.
**Invariant:** The flag-set must cover the WHOLE input set as one atomic step — per-segment setting would allow partial overlap between two plans sharing a segment subset. Every post-CAS failure must release flags synchronously in the same function or segments stay locked forever (the Clean path releases only for tasks that made it into executingTasks). Conflict ≠ error: callers treat ErrCompactionPlanConflict as healthy contention evidence.
**Probe:** Direct-source pin: revalidation comment :607–609; release-on-failure sites :571/:579/:585. Upstream suite `internal/datacoord/compaction_inspector_test.go` covers enqueue/conflict paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "createCompactTask CheckAndSetSegmentsCompacting enqueueCompaction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt atomic multi-resource CAS + synchronous unwind on every later failure for exclusive-use resource scheduling. Adapt conflict taxonomy to your error model. Omit milvus's four-type factory switch. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
