<!-- capsule-v2 -->
# Parallel-safety + context-shift defaults — which model families and options silently override request settings at load?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** What per-family and per-option overrides must a porter replicate for correct multimodal/deepseek behavior?

## load()-time numParallel clamp + supportsContextShift
**Path/Symbol:** `server/sched.go:498-519` (numParallel resolution inside `load`), :136-150 (`resolveContextShift`, `supportsContextShift`). **Signature:** embedded in `func (s *Scheduler) load(req *LlmRequest, ...) bool`.
**Data Shape:** Unsafe-parallel family list: mllama, qwen3vl, qwen3vlmoe, qwen35, qwen35moe, qwen3next, lfm2, lfm2moe, nemotron_h, nemotron_h_moe, nemotron_h_omni. Context shift disabled ONLY for deepseek2 family. Effective server context = `effectiveModelContext(numCtx, f) * max(numParallel,1)`.

### Decisive source
```go
numParallel := max(int(envconfig.NumParallel()), 1)
completion := req.model.CheckCapabilities(model.CapabilityCompletion) == nil
if !completion { numParallel = 1 }              // embedding models: always 1

if slices.Contains([]string{"mllama", "qwen3vl", "qwen3vlmoe", "qwen35", "qwen35moe",
    "qwen3next", "lfm2", "lfm2moe", "nemotron_h", "nemotron_h_moe", "nemotron_h_omni"},
    req.model.Config.ModelFamily) && numParallel != 1 {
    numParallel = 1
    slog.Warn("model architecture does not currently support parallel requests", ...)
}
...
func supportsContextShift(m *Model) bool {
    if m == nil { return true }
    if m.Config.ModelFamily == "deepseek2" || slices.Contains(m.Config.ModelFamilies, "deepseek2") {
        return false                            // RoPE rescale corrupts deepseek2
    }
    return true
}
```

**Flow:** Load computes the EFFECTIVE parallel count before sizing anything; because predicted server context multiplies by numParallel, the clamp must precede `effectiveLlamaServerContext` or VRAM predictions are wrong. ContextShift resolves from an explicit request `*bool` first, else the family rule, and lands in the runner's launch config — it controls whether llama-server may re-base old tokens when history outgrows NumCtx. Both rules ride on `Config.ModelFamily(ies)` strings emitted by GGUF conversion, so new families join by adding to these lists.
**Invariant:** The clamp happens once at load (runner-level slot count), never per request; embedding (non-completion) models ignore OLLAMA_NUM_PARALLEL entirely; a nil model is maximally permissive (shift allowed).
**Probe:** `grep -cF 'slices.Contains([]string{"mllama", "qwen3vl"' server/sched.go` → `1`; `grep -c "numParallel = 1" server/sched.go` → `2` (embedding + unsafe-family). Direct tests: scheduler suite PASS at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "load numParallel completion embedding clamp", limit: 6 });
```

## Verdict
Adopt family-listed overrides resolved once per load with prediction-order coupling. Adapt the family lists as your engine gains safe KV-parallelism; omit contextShift plumbing if your engine always shifts safely.
