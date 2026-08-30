<!-- capsule-v2 -->
# Scheduler two-loop core — how does Ollama serialize model loads while serving already-loaded models in parallel?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How must a porter structure request admission, load serialization, and unload bookkeeping so one model loads at a time without blocking requests to loaded models?

## Scheduler pending/completed loop pair
**Path/Symbol:** `server/sched.go` (`Scheduler.Run`, `processPending`, `processCompleted`, lines 216-458). **Signature:** `func (s *Scheduler) Run(ctx context.Context)` spawning `processPending(ctx)` and `processCompleted(ctx)` goroutines.
**Data Shape:** Four channels sized `envconfig.MaxQueue()`: `pendingReqCh chan *LlmRequest`, `finishedReqCh chan *LlmRequest`, `expiredCh chan *runnerRef`, `unloadedCh chan any`. `loaded map[string]*runnerRef` guarded by `loadedMu`; `activeLoading llm.LlamaServer` is the single in-flight load. Requests carry buffered size-1 `successCh`/`errCh` so neither side blocks on a gone consumer.

### Decisive source
```go
// processPending inner loop: re-check under lock each iteration
pendingKey := schedulerModelKey(pending.model)
s.loadedMu.Lock()
runner := s.loaded[pendingKey]
loadedCount := len(s.loaded)
runnersSnapshot := make([]ml.FilteredRunnerDiscovery, 0, len(s.loaded))
for _, r := range s.loaded { runnersSnapshot = append(runnersSnapshot, r) }
s.loadedMu.Unlock()

if runner != nil {
    if runner.needsReload(ctx, pending) { runnerToExpire = runner }
    else { pending.useLoadedRunner(runner, s.finishedReqCh); break } // usable → serve
} else if maxRunners > 0 && loadedCount >= int(maxRunners) {
    runnerToExpire = s.findRunnerToUnload()
}
```

**Flow:** `getRunner` fast-path attaches an existing healthy runner (`useLoadedRunner`: refCount++, stop expireTimer) else pushes onto `pendingReqCh` (non-blocking; full queue ⇒ immediate `ErrMaxQueue`). `processPending` pops ONE pending request and spins an inner `for{}` until that model is served or failed: reload-check → evict-victim path (`findRunnerToUnload` → set `sessionDuration=0`, push to `expiredCh` only when refCount≤0) → wait `<-s.unloadedCh` → retry. `load()` runs synchronously inside this loop, enforcing "only one model loads at a time"; requests to other already-loaded models never enter the queue at all (fast-path), so they proceed concurrently. `processCompleted` owns three events: finished (refCount--; arm/reset `expireTimer = time.AfterFunc(sessionDuration)`), expired (retry via 10ms goroutine requeue while refCount>0; pid-mismatch ⇒ orphan cleanup WITHOUT deleting the loaded entry; else `waitForVRAMRecovery` + `unload()` + `delete(s.loaded,...)` then `unloadedCh <- struct{}{}`), keeping ALL map mutation in one goroutine.
**Invariant:** `loaded` map is mutated only by `processCompleted` (insert happens in `load()` under `loadedMu`, removal only in the expired branch); every eviction wait consumes exactly one `unloadedCh` signal per evicted runner — `evictAllAndWait` counts its loop iterations off the number of victims it queued.
**Probe:** `grep -c "expiredCh <- runner" server/sched.go` → `8` sites; `grep -c "refCount++" server/sched.go` → `2` (useLoadedRunner :478 and post-wait :744); direct tests `server/sched_test.go` `TestSchedulerTracksMultipleLoadedRunners`, `TestSchedLlamaServerEvictsExistingOnPending` (both PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "Scheduler getRunner useLoadedRunner processPending", limit: 10 });
```

## Verdict
Adopt the two-loop shape (single loader thread + single reaper thread over channels, refCount+expireTimer lifecycle, non-blocking admission with ErrMaxQueue backpressure). Adapt channel sizes/keepalive defaults to host policy. Omit MLX/cloud branches and Windows-specific mmap logic when porting the scheduling kernel alone.
