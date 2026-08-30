<!-- capsule-v2 -->
# OOM retry ladder — what happens when a model load or a running generation hits out-of-memory?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How does the scheduler recover from OOM without infinite retry loops, and which knobs may it auto-reduce?

## Load-time preflight + crash/OOM ladder
**Path/Symbol:** `server/sched.go` (`Scheduler.load` lines 496-755, preflight :562-584, `reduceAutoNumCtxForLoadOOM` :748-786, `evictAllAndWait` :1590-1630, runtime path `expireRunnersForRuntimeOOM` :1632-1653). **Signature:** `func (s *Scheduler) load(req *LlmRequest, systemInfo ml.SystemInfo, gpus []ml.DeviceInfo, requireFull bool) bool` — return value means "evict needed, retry me".
**Data Shape:** `req.oomRetryAttempted bool` latches after the FIRST OOM/crash retry; `numCtxAuto/numBatchAuto/useMMapAuto` mark scheduler-derived (not user) values eligible for reduction.

### Decisive source
```go
// Pre-flight: llama-server auto-detects layers, so predict-and-evict BEFORE spawning.
if requireFull && !explicitPartialGPUOffload(launchOpts, f) && len(s.loaded) > 0 && len(loadGpus) > 0 {
    freeMemory, gpuFreeMemory, systemLimited := availableMemoryForPlacement(systemInfo, loadGpus, launchOpts)
    if predictedForLoad > freeMemory*80/100 {   // 20% headroom
        ...
        s.loadedMu.Unlock(); return true        // evict, then retry load
    }
}
// Post-crash ladder inside processPending:
if pending.oomRetryAttempted {
    if !s.evictAllAndWait(ctx, pendingKey) { return } // wait EVERY unload signal
    continue                                           // single retry, then fail-fast
}
```

**Flow:** (1) Predict server VRAM (`PredictServerVRAM`) + batch surcharge; if >80% of free memory with other models resident ⇒ evict-before-spawn. (2) Spawn failure / `ErrLoadRequiredFull`: if `requireFull=false` and nothing else loaded ⇒ hard error; if OOM and `!oomRetryAttempted` and ctx/batch are auto ⇒ reduce (`nextLowerAutoNumCtx`: >32768→32768, >4096→4096, else give up; recompute NumBatch) and return true; else if OOM with others loaded ⇒ set latch, return true → caller runs `evictAllAndWait(keepKey=pending)` which expires every OTHER runner (only those with refCount≤0 get queued) then consumes exactly one `unloadedCh` per victim before the single retry. (3) Second OOM falls through to `req.errCh`. (4) Runtime OOM during generation: ChatHandler calls `expireRunnersForRuntimeOOM(m, err)` — zeroing sessionDuration of all loaded runners so they unload when idle, then streams the error to the client.
**Invariant:** The latch makes every path at-most-one automatic retry — a persistent failure surfaces as an error instead of an eviction storm; explicit (non-auto) user options are never silently reduced (`TestSchedLoadOOMKeepsExplicitContextBeforeRetry`).
**Probe:** `grep -c "oomRetryAttempted" server/sched.go` → `8` sites; `grep -c "80/100" server/sched.go` → `3` headroom checks; `grep -c "return 32768, true" server/sched.go` → `1`. Direct tests `server/sched_test.go`: `TestSchedLoadCrashTriggersEvictAllAndRetry`, `TestSchedLoadOOMReducesAutomaticContextBeforeRetry`, `TestSchedLoadOOMKeepsExplicitContextBeforeRetry`, `TestSchedLoadCrashNoOtherModelsFailsFast`, `TestSchedRuntimeOOMExpiresLoadedRunners` (all PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "evictAllAndWait OOM retry evict", limit: 5 });
```

## Verdict
Adopt the three-stage shape: predict-evict before spawn, one-shot auto-degrade (context tier, batch) + evict-all-and-retry with a latch, runtime-OOM idle-expiry. Adapt thresholds/headroom percentages to your hardware accounting; omit llama-server-specific prediction if your backend reports exact needs.
