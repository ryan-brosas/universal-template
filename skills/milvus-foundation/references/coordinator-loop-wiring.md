<!-- capsule-v2 -->
# Compaction scheduling loop wiring — how do the three goroutines (trigger, schedule, clean) compose into one coordinator service?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** What starts what — and in which order do trigger manager, inspector loops, and GC run relative to each other?

## start/stop topology
**Path/Symbol:** `internal/datacoord/compaction_trigger_v2.go:Start/Stop/loop` (208–275); `internal/datacoord/compaction_inspector.go:start` (309–313), `loopSchedule` (371–388), `loopClean` (390–405), `stop` (482–487); `checkSchedule` composition (200–207).
**Signature:** `func (c *compactionInspector) checkSchedule() { checkCompaction → cleanFailedTasks → schedule }`; stopCh + stopOnce + stopWg trio.
**Data Shape:** Tickers: CompactionScheduleInterval (fast), CompactionGCIntervalInSeconds (slow). Trigger manager has its OWN context-cancel lifecycle independent of inspector's channel.

### Decisive source
```go
func (c *compactionInspector) checkSchedule() {
	err := c.checkCompaction()
	if err != nil {
		mlog.Info(context.TODO(), "fail to update compaction", mlog.Err(err))
	}
	c.cleanFailedTasks()
	c.schedule()
}
```
```go
func (c *compactionInspector) stop() {
	c.stopOnce.Do(func() { close(c.stopCh) })
	c.stopWg.Wait()
}
```

**Flow:** Server wires meta → segmentManager → inspector → triggerManager. Inspector.start launches TWO goroutines: fast loop (every schedule interval: advance task state machines via Process, hand failed/timeout to cleaners, then drain queue through the exclusion lattice) and slow loop (GC cleaned metas + partition stats). TriggerManager.start runs its six-ticker select on a cancelable context; policies call inspector.enqueueCompaction which is safe from any goroutine (queue is mutex'd). Shutdown: cancel context AND close stopCh once (sync.Once guards double-close), WaitGroup joins both loops.
**Invariant:** Per tick the order matters — state machines advance BEFORE scheduling so freed slots are visible in the same pass, and failed-task cleanup precedes queue drain so Clean()'s segment unlocks unblock waiting work. stopOnce+close(channel) is the canonical Go multi-goroutine shutdown; never close twice.
**Probe:** Direct-source pin: composition :200–207. Upstream suites cover components individually (`compaction_inspector_test.go`, `compaction_trigger_v2_test.go`); full wiring is integration-tested (`tests/integration/`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "checkSchedule loopSchedule loopClean compactionInspector start", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-loop cadence (fast control / slow GC) with ordered per-tick phases for any long-lived coordinator. Adapt intervals to your scale. Omit milvus metrics plumbing. Caveat: cgo-blocked runner; direct source read at pin.
