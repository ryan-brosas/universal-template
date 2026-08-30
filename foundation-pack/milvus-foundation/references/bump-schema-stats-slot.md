<!-- capsule-v2 -->
# Bump-schema compaction & sort-task slot — how does a metadata-only "compaction" rewrite schema version, and how is a stats task priced?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What distinguishes BumpSchemaVersionCompaction from mix in plan build and meta mutation, and what does calculateStatsTaskSlot do with segment size?

## bumpSchemaVersionTask saveSegmentMeta + stats slot pricing
**Path/Symbol:** `internal/datacoord/compaction_task_bump_schema_version.go` (BuildCompactionRequest 93–148, QueryTaskOnWorker 148+, saveSegmentMeta 357–384); `calculateStatsTaskSlot` (datacoord, referenced by mix GetTaskSlot :57–65).
**Signature:** `func (t *bumpSchemaVersionTask) BuildCompactionRequest() (*datapb.CompactionPlan, error)`; `saveSegmentMeta Method internal/datacoord/compaction_task_bump_schema_version.go 357-384` (graph-pinned).
**Data Shape:** Same CompactionPlan wire type as mix but Type=BumpSchemaVersionCompaction; carries the NEW schema + PreAllocatedSegmentIDs (it re-segments). Shares the scheduler's task.Task interface via GetTaskSlot.

### Decisive source
```go
// mixCompactionTask.GetTaskSlot, sort branch:
if t.GetTaskProto().GetType() == datapb.CompactionType_SortCompaction {
    segment := t.meta.GetHealthySegment(context.Background(), t.GetTaskProto().GetInputSegments()[0])
    if segment != nil {
        segSize := segment.getSegmentSize()
        slotUsage = calculateStatsTaskSlot(segSize)
        mlog.Info(context.TODO(), "mixCompactionTask get task slot",
            mlog.Int64("segment size", segSize), mlog.Int64("task slot", slotUsage))
    }
}
```
**Flow:** Schema-bump tasks reuse the ENTIRE mix machinery — same state machine, same CreateTaskOnWorker/QueryTaskOnWorker ladder, same CompleteCompactionMutation dispatch to `completeBumpSchemaVersionCompactionMutation` (which swaps segments while rewriting their schema version) — differing only in plan Type and that its trigger exists to propagate schema evolution to old-format segments. Sort compaction rides mix too (`SortCompaction` shares the mix class) but prices slots proportionally to input segment size instead of flat config, so one huge segment can't monopolize a small node.
**Invariant:** Metadata-evolution work must flow through the SAME admission/state/GC machinery as data rewrite work or it escapes snapshot gates and CAS protection. Size-priced slots need a healthy-input guard: missing segment ⇒ fall back to flat config rather than fail scheduling.
**Probe:** `internal/datacoord/compaction_task_mix_test.go` suite covers shared machinery; direct-source pin: sort-slot branch :56–66. Upstream `compaction_task_bump_schema_version_test.go` (947L) pins the bump variant.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "bumpSchemaVersionTask saveSegmentMeta calculateStatsTaskSlot", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI resolves `internal.datacoord.saveSegmentMeta Method internal/datacoord/compaction_task_bump_schema_version.go 357-384`.)

## Verdict
Adopt piggybacking metadata migrations on existing rewrite pipelines with distinct plan typing. Adapt slot-pricing curve to your worker memory profile. Omit milvus schema-version guard specifics. Caveat: cgo-blocked runner; direct source + upstream tests read at pin.
