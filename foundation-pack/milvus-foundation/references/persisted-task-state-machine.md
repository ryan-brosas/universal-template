<!-- capsule-v2 -->
# Persisted task state machine — how do you drive a long-running distributed task through states with every transition crash-safe in meta?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What is the exact state machine for a compaction task (pipelining → executing → …), and which write-ordering rules keep a crashed coordinator from leaking locked segments or losing completed work?

## ShadowClone + updateAndSaveTaskMeta + terminal-state gating
**Path/Symbol:** `internal/datacoord/compaction_task.go:CompactionTask` interface (lines 24–48) and `internal/datacoord/compaction_task_mix.go:mixCompactionTask` (Process :253–271, CreateTaskOnWorker :83–118, QueryTaskOnWorker :120–175, saveSegmentMeta :223–249, doClean :307–318, updateAndSaveTaskMeta :320–337).
**Signature:** `Process() bool` (true = state machine ENDED — completed, failed OR timeout); `updateAndSaveTaskMeta(opts ...compactionTaskOpt) error`; `ShadowClone(opts ...compactionTaskOpt) *datapb.CompactionTask`.
**Data Shape:** `taskProto atomic.Value // *datapb.CompactionTask`. Functional options: setState/setNodeID/setFailReason/setEndTime/setResultSegments/setStartTime/setRetryTimes. States: pipelining, executing, analyzing, indexing, meta_saved, statistic, completed, failed, timeout, cleaned.

### Decisive source
```go
func (t *mixCompactionTask) doClean() error {
	err := t.updateAndSaveTaskMeta(setState(datapb.CompactionTaskState_cleaned))
	if err != nil { return err }
	// resetSegmentCompacting must be the last step of Clean, to make sure
	// resetSegmentCompacting only called once
	// otherwise, it may unlock segments locked by other compaction tasks
	t.resetSegmentCompacting()
	return nil
}
```
```go
// CreateTaskOnWorker: DataNode slot-limit refusal demotes the task back to
// pending by resetting the node id — retry happens in checkCompaction():
err = t.updateAndSaveTaskMeta(setState(datapb.CompactionTaskState_pipelining), setNodeID(NullNodeID))
```

**Flow:** enqueue (`pipelining`, node unassigned) → `CreateTaskOnWorker`: BuildCompactionRequest then `cluster.CreateCompaction`; worker refusal ⇒ back to `pipelining` + NullNodeID (metrics moved Executing→Pending) so a slot-limited node is retried elsewhere; success ⇒ `executing`. → `QueryTaskOnWorker` polls: query RPC error/nil result ALSO demotes to `pipelining`+NullNodeID; `completed` result ⇒ `ValidateSegmentStateBeforeCompleteCompactionMutation` then `saveSegmentMeta` (compress binlogs → `CompleteCompactionMutation` transactional swap → metricMutation.commit() AFTER successful meta update → non-blocking push to build-index channel) → `meta_saved` → `processMetaSaved` sets `completed`. `checkCompaction` calls `Process()` per executing task on each tick; finished tasks move failed/timeout/completed into `cleaningTasks`; `cleanFailedTasks` runs `Clean()` which persists `cleaned` BEFORE `resetSegmentCompacting()` as its final statement.
**Invariant:** Every state change is persist-first (`saveTaskMeta(clone)` succeeds before `SetTask` publishes to the atomic.Value). Terminal states get EndTime appended automatically (:322–328). Segment compacting-flags are released exactly once and only after the `cleaned` meta write lands — releasing first would unlock segments another live task owns. `meta_saved` exists so segment-meta swap and task-complete are separately resumable crashes. `NeedReAssignNodeID` = state pipelining AND node 0/NullNodeID.
**Probe:** `internal/datacoord/compaction_task_mix_test.go:276 TestProcess` and `:300 TestQueryTaskOnWorker`; `internal/datacoord/compaction_task_l0_test.go:82 TestProcessRefreshPlan_NormalL0`, `:139 _SegmentNotFoundL0`, `:161 _SelectZeroSegmentsL0`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "mixCompactionTask Process saveSegmentMeta CompleteCompactionMutation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the option-functional persisted state machine with persist-before-publish ordering and last-step unlock for any coordinator-managed distributed job. Adapt state vocabulary to your domain. Omit milvus's binlog compression and index-channel plumbing. Caveat: cgo-blocked runner — direct source + upstream tests read at pin.
