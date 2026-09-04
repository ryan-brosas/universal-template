<!-- capsule-v2 -->
# Persisted task-meta reload & upgrade compatibility — how do you load years-old in-flight tasks after a version upgrade without corrupting either generation?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** At startup, which persisted compaction tasks are resumed, which are marked failed, and why is L0 exempt from the new-field failure rule?

## reloadFromKV compatibility gate + clone-on-read meta
**Path/Symbol:** `internal/datacoord/compaction_task_meta.go:reloadFromKV` (lines 82–113), `SaveCompactionTask`/`DropCompactionTask` (163–198), `GetCompactionTasksByCollection` (130–148); `internal/datacoord/compaction_inspector.go:loadMeta` (315–369).
**Signature:** `func (csm *compactionTaskMeta) reloadFromKV() error`; store shape `map[triggerID]map[planID]*datapb.CompactionTask` under embedded RWMutex + 512-entry/15-min expirable stats LRU.
**Data Shape:** Newer field under test: `task.PreAllocatedSegmentIDs`. Finished-state predicate: `isCompactionTaskFinished(task)`.

### Decisive source
```go
// Compatibility handling: for milvus ≤v2.4, since compaction task has no
// PreAllocatedSegmentIDs field, here we just mark the task as failed and wait
// for the compaction trigger to generate a new one.
//
// NOTE:
// - Only compaction tasks that require pre-allocated segment IDs should be
//   marked as failed when PreAllocatedSegmentIDs is nil.
// - Level0DeleteCompaction tasks never use PreAllocatedSegmentIDs and must be
//   ignored here, otherwise unfinished L0 delete compaction tasks created
//   before upgrade will be incorrectly marked as failed on reload.
if !isCompactionTaskFinished(task) &&
    task.PreAllocatedSegmentIDs == nil &&
    task.GetType() != datapb.CompactionType_Level0DeleteCompaction {
    task.State = datapb.CompactionTaskState_failed
    task.FailReason = fmt.Sprintf("PreAllocatedSegmentIDs is nil, taskID: %v", task.GetPlanID())
}
```

**Flow:** Startup: list all persisted tasks; unfinished+nil-new-field+not-L0 ⇒ rewritten to failed IN MEMORY (original KV untouched) and cached — the trigger regenerates them with proper fields. Every surviving task enters the trigger→planID nested map. `loadMeta` (inspector) then walks the cache: cleaned-state tasks abandoned; others re-materialized via `createCompactTask`; needing node ⇒ re-submit through the normal queue (drop-on-failure), else `restoreTask` straight into executingTasks + scheduler. All reads CLONE (`proto.Clone`) before returning — callers can never mutate cache contents. Drop deletes empty trigger buckets.
**Invariant:** Upgrade rules must be scoped by task TYPE, not just field presence: a field one type never uses would otherwise fail every pre-upgrade instance of that type on first boot after upgrade. Failed-marking is memory-only so a rollback deployment sees its original data. Clone-on-read is absolute; Save persists to catalog BEFORE updating memory.
**Probe:** Direct-source pin: NOTE comment :89–97. Upstream suite `internal/datacoord/compaction_task_meta_test.go` covers save/drop/reload; inspector restart behavior pinned in `compaction_inspector_test.go`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "compactionTaskMeta reloadFromKV PreAllocatedSegmentIDs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt type-scoped compatibility shims + clone-on-read caches for any persisted work-store that crosses version upgrades. Adapt the exempt-type list to your field usage matrix. Omit milvus's metrics-stats LRU unless porting observability too. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
