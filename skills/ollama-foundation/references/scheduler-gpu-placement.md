<!-- capsule-v2 -->
# GPU placement selector — which GPUs should host a new llama-server, and when does one GPU win over a group?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How is the device set for a model load chosen among mixed vendors, iGPUs/dGPUs, explicit main_gpu requests, and spread-vs-single policy?

## Placement decision tree
**Path/Symbol:** `server/sched.go:972-1037` (`selectLlamaServerPlacement`, `singleLlamaServerGPUPlacement`) plus comparators `betterPlacementGPU` :1078-1084 / `betterPlacementGroup` :1100-1108 and fit finders `bestSingleGPUFit` :1052-1071 / `bestGPUGroupByAvailableMemory`. **Signature:** `func selectLlamaServerPlacement(systemInfo ml.SystemInfo, gpus []ml.DeviceInfo, predictedVRAM uint64, opts api.Options) ([]ml.DeviceInfo, api.Options)`.
**Data Shape:** `gpus` grouped by backend library via `ml.ByLibrary` (mixed CUDA+ROCm never co-host). Returns the chosen device slice AND possibly-mutated launch options (`MainGPU` pinned to 0 when a single device wins).

### Decisive source
```go
if len(gpus) <= 1 || opts.NumGPU == 0 { return gpus, launchOpts }  // CPU-only or no split
groups := ml.ByLibrary(gpus)
if opts.MainGPU != nil { ...bestExplicitMainGPU... }                // user pin honored per group
if !envconfig.SchedSpread() && predictedVRAM > 0 {
    gpu, available, ok := bestSingleGPUFit(systemInfo, groups, predictedVRAM)
    if ok { // fits in ONE device at ≤80% of its free memory
        selected, launchOpts := singleLlamaServerGPUPlacement(gpu, launchOpts)
        ...
        return selected, launchOpts
    }
}
selected := bestGPUGroupByAvailableMemory(systemInfo, groups)       // multi-GPU tensor split
return selected, launchOpts
```

**Flow:** Skip entirely for ≤1 device or `NumGPU==0` → honor explicit `main_gpu` (searching every library group; warn-and-pass-through when the index lives outside the winning group) → unless spread is forced, try single-GPU fit where a candidate qualifies only if `predictedVRAM <= candidateAvailable*80/100` → fall back to the whole best group. Comparators rank discrete over integrated first, then raw available memory; iGPU availability clamps to system free RAM because shared-memory devices report static baselines (`availableMemoryForGPU`: `min(gpu.FreeMemory, systemInfo.FreeMemory)`).
**Invariant:** Mixed-vendor groups are never merged into one placement; a single-GPU placement always rewrites MainGPU to 0 so llama-server sees exactly one device; integrated-GPU "free" numbers must be discounted by live system free memory or loads will overshoot shared RAM.
**Probe:** `grep -c "return !candidate.Integrated" server/sched.go` → `1`; `grep -c "SchedSpread()" server/sched.go` → `1`; `grep -cF "systemInfo.FreeMemory < sharedGPUFree" server/sched.go` → `1`. Direct tests: `server/sched_test.go` `TestSchedLlamaServerExplicitPartialNumGPUSkipsFullFitEviction`, `TestSchedLlamaServerFitsAlongside`, `TestSchedLlamaServerPredictionUsesTotalParallelContext` (PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "selectLlamaServerPlacement GPU group placement", limit: 5 });
```

## Verdict
Adopt the decision order (explicit pin → single-device 80% fit → best group) plus discrete-over-integrated preference and iGPU/RAM clamp. Adapt the 80% constant and grouping key to your stack; omit multi-backend vendor partitioning if you only target one accelerator family.
