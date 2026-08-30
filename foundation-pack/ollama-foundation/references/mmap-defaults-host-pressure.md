<!-- capsule-v2 -->
# mmap defaults + host-pressure guard — when must a load disable memory-mapped weights?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** What conditions flip mmap off at load time, and why can disabling it HURT under VRAM pressure?

## disableMmapDefaultReason + maybeDisableMmapForHostPressure
**Path/Symbol:** `server/sched.go:1152-1235` (`applyLlamaServerMmapDefaults`, `disableMmapDefaultReason`, `maybeDisableMmapForHostPressure` :1200-1248, `mmapHostPressureHeadroom` :1255-1260), free-space reconciliation `updateFreeSpace` :1276-1322. **Signature:** `func disableMmapDefaultReason(goos string, opts api.Options, gpus []ml.DeviceInfo, blockCount, predictedVRAM, availableVRAM uint64) string`.
**Data Shape:** Returns a reason string ("" = keep mmap): `cpu`, `windows_cuda`, `metal_partial_offload`, host-pressure path sets UseMMap=false with `useMMapAuto=true`. Explicit user UseMMap always wins (first check returns "").

### Decisive source
```go
if opts.UseMMap != nil { return "" }                       // user explicit → never override
if opts.NumGPU == 0 || len(gpus) == 0 || allDevicesLibrary(gpus, "cpu") { return "cpu" }
if goos == "windows" && hasDeviceLibrary(gpus, "cuda") { return "windows_cuda" }
if hasDeviceLibrary(gpus, "metal") {
    if opts.NumGPU > 0 && blockCount > 0 && uint64(opts.NumGPU) < blockCount+1 { return "metal_partial_offload" }
    if opts.NumGPU < 0 && predictedVRAM > 0 && availableVRAM > 0 && predictedVRAM > availableVRAM {
        return "metal_partial_offload" }
}
// host-pressure arm — only while the model still FITS on GPU:
if predictedVRAM == 0 || availableVRAM == 0 || predictedVRAM > availableVRAM*80/100 { return false }
pressure := modelSize + loadedMmapSize + mmapHostPressureHeadroom(systemInfo.TotalMemory)
return systemInfo.FreeMemory < pressure
```

**Flow:** Applied during load before spawning. CPU-only loads drop mmap (page-cache games buy nothing); Windows+CUDA needs anonymous memory for stable WDDM behavior; Metal partial offloads disable so non-offloaded layers don't double-map. The subtle arm: on systems where RAM is nearly exhausted by OTHER mmap'd model files plus headroom (`max(8GiB, total/10)`), turn THIS load's mmap off — but ONLY when the model still fits VRAM (≤80% threshold). Under real VRAM pressure disabling mmap makes partial CPU offload WORSE by converting file-backed pages into anonymous ones, hence the early-out. `updateFreeSpace` complements this per placement decision by subtracting each loaded runner's measured `VRAMByGPU` from reported free and taking the smaller (laggy driver reports vs predictions).
**Invariant:** User-specified options are never overridden; the host-pressure heuristic must never fire when the model doesn't fit VRAM anyway; auto-flag (`useMMapAuto`) records that the scheduler chose it so needsReload treats later auto values as equal.
**Probe:** `grep -cF "return \"\"" server/sched.go` → count includes explicit-option early-out; `grep -nF "mmapHostPressureHeadroom" server/sched.go` → def+use; `grep -cF "80/100" server/sched.go` → `3`. Direct tests: scheduler suite PASS at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "disableMmapDefaultReason mmap pressure", limit: 6 });
```

## Verdict
Adopt reason-coded default overrides with the fits-in-VRAM guard around the host-pressure arm. Adapt thresholds to your OS/driver matrix; omit platform arms you don't ship.
