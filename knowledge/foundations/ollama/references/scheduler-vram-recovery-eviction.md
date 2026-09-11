<!-- capsule-v2 -->
# VRAM-recovery wait + eviction victim choice — when is it safe to load the next model after an unload?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How do you avoid loading a replacement model into VRAM the driver hasn't released yet, and which runner gets evicted?

## waitForVRAMRecovery + findRunnerToUnload
**Path/Symbol:** `server/sched.go` (`waitForVRAMRecovery` :1441-1499, `findRunnerToUnload` :1656-1693, `ByDurationAndName` :1557-1575, duplicate-event guards in `processCompleted` :395-440). **Signature:** `func (s *Scheduler) waitForVRAMRecovery(runner *runnerRef, runners []ml.FilteredRunnerDiscovery) chan any`.
**Data Shape:** Returns a buffered chan signaled on convergence OR timeout (`waitForRecovery = 5s`, poll ticker `250ms`). Skipped entirely for zero-GPU runners, all-integrated runners, or single Metal device (unified memory reports instantly).

### Decisive source
```go
gpusBefore := s.getGpuFn(context.Background(), runners) // baseline BEFORE unload
...
// inside poll loop:
if float32(freeMemoryNow-freeMemoryBefore) > float32(runner.vramSize)*0.75 {
    finished <- struct{}{}   // ≥75% of the runner's VRAM reappeared → proceed
}
```
```go
sort.Sort(ByDurationAndName(runnerList))   // shortest keepalive, then lex model key
for _, runner := range runnerList {
    rc := runner.refCount
    if rc == 0 { return runner }           // prefer any IDLE runner
}
return runnerList[0]                       // else shortest-duration victim
```

**Flow:** The reaper calls `waitForVRAMRecovery` BEFORE `unload()` so a before/after baseline exists; `delete(s.loaded,...)` happens under `loadedMu`, then the goroutine blocks on `<-finished` and only THEN emits `unloadedCh` — so every waiter resumes into converged memory. Victim selection: idle-first (refCount==0), tie-broken by shortest session duration then name for determinism. Double-expire safety: an expired event with refCount>0 requeues itself after 10ms; a nil map entry means "already unloaded" and is ignored; pid mismatch means an orphaned twin — shut the orphan down WITHOUT deleting the live loaded entry.
**Invariant:** Never emit `unloadedCh` before VRAM convergence (or its 5s timeout); never evict a runner with positive refCount directly — queue it and let the refCount drain; the expired path must tolerate duplicate events idempotently because cancel-during-load can produce them.
**Probe:** `grep -cF "runner.pid != runnerToUnload.pid" server/sched.go` → `1`; `grep -cF "float32(runner.vramSize)*0.75" server/sched.go` → `1`; `grep -cF "250 * time.Millisecond" server/sched.go` → `1`. Direct tests: `go test ./server/ -run TestSched` battery incl. `TestSchedulerTracksMultipleLoadedRunners` (PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "waitForVRAMRecovery convergence unload", limit: 5 });
```

## Verdict
Adopt baseline-before-unload + 75%-convergence-or-timeout polling and the idle→shortest-duration victim ladder. Adapt the 5s/250ms constants to your driver's release latency; skip the wait entirely on unified-memory backends as Ollama does for Metal/iGPU.
