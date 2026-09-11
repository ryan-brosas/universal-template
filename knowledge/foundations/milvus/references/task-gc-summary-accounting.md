<!-- capsule-v2 -->
# Compaction task GC & summary accounting — how do finished tasks get dropped from meta, and what counts as "executing" in status views?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** After a task reaches completed/failed/timeout/cleaned, when is its meta row actually deleted, and how does the user-facing state summary aggregate ten internal states?

## cleanCompactionTaskMeta drop-tolerance + summaryCompactionState rollup
**Path/Symbol:** `internal/datacoord/compaction_inspector.go:cleanCompactionTaskMeta` (lines 412–430), `summaryCompactionState` (103–163), `Clean`/`loopClean` (390–410), `maxCompactionTaskExecutionDuration` map (44–50), `checkDelay` (703–717).
**Signature:** `func summaryCompactionState(triggerID int64, tasks []*datapb.CompactionTask) *compactionInfo`; GC loop interval `DataCoordCfg.CompactionGCIntervalInSeconds`; drop tolerance `CompactionDropToleranceInSeconds`.
**Data Shape:** `compactionInfo{state Executing|Completed, executingCnt, completedCnt, failedCnt, timeoutCnt, mergeInfos}`. Ten datapb states rolled up.

### Decisive source
```go
for _, task := range tasks {
    if task.State == datapb.CompactionTaskState_cleaned {
        duration := time.Since(time.Unix(task.StartTime, 0)).Seconds()
        if duration > Params.DataCoordCfg.CompactionDropToleranceInSeconds.GetAsDuration(time.Second).Seconds() {
            // try best to delete meta
            err := c.meta.DropCompactionTask(context.TODO(), task)
```
```go
ret.executingCnt = executingCnt + pipeliningCnt + analyzingCnt + indexingCnt + metaSavedCnt + stats
...
if ret.executingCnt != 0 {
    ret.state = commonpb.CompactionState_Executing
} else {
    ret.state = commonpb.CompactionState_Completed
}
```

**Flow:** Two inspector loops: fast `loopSchedule` tick drives checkSchedule/cleanFailedTasks; slow `loopClean` (GC interval) runs cleanCompactionTaskMeta — only tasks already in `cleaned` state are eligible, and only after StartTime ages past drop tolerance; failures are logged and retried next tick ("try best"). Partition-stats GC in the same Clean keeps the newest two versions per channel. Status queries (`getCompactionInfo`) recompute from meta each call: six states count as executing (incl. pipelining and meta_saved!), completed/failed/timeout tally separately; any executing ⇒ global Executing else Completed. checkDelay warns rate-limited when a type exceeds its max duration (mix/L0 30m, clustering 60m, sort 20m).
**Invariant:** Meta deletion is decoupled from logical completion by one full tolerance window so late readers of mergeInfos still resolve; deletion is best-effort idempotent. The public binary state hides pipelining/meta_saved/analyzing/indexing inside "Executing" — porting a status API must preserve that rollup or clients see flapping Completed during handoffs.
**Probe:** Direct-source pins: tolerance comment :420–421; rollup sum :138. Upstream suite `internal/datacoord/compaction_inspector_test.go` exercises schedule/clean paths; `TestCheckDelay` :1100 pins delay warning.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "cleanCompactionTaskMeta summaryCompactionState checkDelay", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt delayed best-effort GC plus explicit internal→public state rollups for long-running task systems. Adapt durations/tolerance to your SLAs. Omit partition-stats version retention unless porting stats lineage too. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
