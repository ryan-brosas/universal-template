<!-- capsule-v2 -->
# Compaction scheduler type-exclusion lattice — how do you drain a priority queue while guaranteeing per-channel mutual exclusion across incompatible compaction types?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** When a central scheduler pops tasks from one shared priority queue, how does it prevent two mutually-exclusive task types (L0-delete vs mix vs clustering) from running concurrently on the same channel/partition without ever deadlocking or starving?

## Scheduler exclusion sets + deferred requeue
**Path/Symbol:** `internal/datacoord/compaction_inspector.go:schedule` (lines 209–307).
**Signature:** `func (c *compactionInspector) schedule() []CompactionTask`.
**Data Shape:** Five exclusion `typeutil.Set[string]`: `l0ChannelExcludes`, `mixChannelExcludes`, `clusterChannelExcludes`, `mixLabelExcludes`, `clusterLabelExcludes`. Labels are `"<partitionID>-<channel>"` strings from `task.GetLabel()`; channels are virtual-channel names. `excluded []CompactionTask` is requeued via a `defer`.

### Decisive source
```go
excluded := make([]CompactionTask, 0)
defer func() {
    // Add back the excluded tasks
    for _, t := range excluded {
        c.queueTasks.Enqueue(t)
    }
}()

for {
    t, err := c.queueTasks.Dequeue()
    if err != nil {
        break // 1. no more task to schedule
    }
    switch t.GetTaskProto().GetType() {
    case datapb.CompactionType_Level0DeleteCompaction:
        if mixChannelExcludes.Contain(...) || clusterChannelExcludes.Contain(...) {
            excluded = append(excluded, t)
            continue
        }
        l0ChannelExcludes.Insert(...)
        selected = append(selected, t)
    ...
```

**Flow:** (1) Sync prioritizer BEFORE the empty-queue early return so config changes made while idle are still adopted (comment lines 212–215); (2) seed exclusion sets by scanning currently-executing tasks under `executingGuard.RLock`; (3) loop: dequeue head → check its type against the OTHER types' exclusion sets → if blocked, park in `excluded` and continue; if schedulable, insert its own channel/label into its OWN set and select it; (4) selected tasks are registered into `executingTasks[planID]` and handed to the global scheduler inside one `executingGuard.Lock()` block; (5) deferred re-enqueue returns parked tasks after the loop.
**Invariant:** An L0 task may not run concurrently with ANY other compaction on its channel (L0 writes delta logs applicable to every segment on that channel); mix/sort/bump share channel-level exclusion with L0 plus label-level exclusion visible to clustering; clustering excludes on channel AND label vs L0/mix. A popped-but-parked task is never lost: the deferred requeue runs even if the loop returns early. Exclusion is enforced at SCHEDULING time, not enqueue time — the queue itself stays order-agnostic.
**Probe:** `internal/datacoord/compaction_queue_test.go` pins queue mechanics; `TestConcurrency` (:146) exercises concurrent Enqueue/Dequeue. Direct-source pin: the defer-requeue comment block sits at lines 243–249 and the empty-set sync-before-return comment at 212–215.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "compactionInspector schedule Dequeue SyncPrioritizer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exclusion-set lattice + deferred requeue pattern verbatim for any multi-type work scheduler sharing one admission queue. Adapt set keys to your domain (channel→shard, label→tenant). Omit milvus metrics emission (`DataCoordCompactionTaskNum` gauge flips Pending→Executing) — replace with your own observability. Caveat: upstream runner needs cgo `milvus_core`; behavior evidence here is direct-source reading plus the package's own unit tests, which were not executable in the mining environment.
