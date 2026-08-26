<!-- capsule-v2 -->
# Automatic NumBatch sizing — how is the generation batch chosen and why does it carry a VRAM surcharge?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How do you pick a default generation batch (NumBatch) from context length and free memory without pushing a load over the memory cliff?

## automaticGenerationBatch ladder
**Path/Symbol:** `server/sched.go:788-926` (constants :790-797, `applyAutomaticGenerationBatch` :804-812, `automaticGenerationBatch` :822-835, `generationBatchFits` :872-884, `generationBatchHasHeadroom` :886-895, `generationBatchSurcharge` :903-911). **Signature:** `func automaticGenerationBatch(effectiveCtx int, predictedVRAM, availableMemory uint64, flashAttention ml.FlashAttentionType, gpus []ml.DeviceInfo) int`.
**Data Shape:** Batch tiers {512 default, 256 CUDA-constrained, 1024 medium (>4096 ctx), 2048 large (>32768 ctx)}; headroom gates 75% (medium) / 60% (large); surcharges 2 GiB (large) / 768 MiB (medium) added to predicted load size.

### Decisive source
```go
if flashAttention == ml.FlashAttentionDisabled && hasCUDADevice(gpus) {
    if constrainedCUDAWithoutFlashAttention(effectiveCtx, gpus) { return llamaServerGenerationBatchConstrained } // ≤8GiB CUDA & ctx>4096 → 256
    return llamaServerGenerationBatchDefault                                                                     // → 512
}
batch := generationBatchForContext(effectiveCtx)
for batch > llamaServerGenerationBatchDefault && !generationBatchFits(batch, predictedVRAM, availableMemory) {
    batch = nextLowerGenerationBatch(batch)
}
```
```go
func generationBatchSurcharge(batch int) uint64 {
    switch {
    case batch >= llamaServerGenerationBatchLarge:  return 2 * format.GibiByte
    case batch >= llamaServerGenerationBatchMedium: return 768 * format.MebiByte
    default:                                        return 0
    }
}
```

**Flow:** Only applied when BOTH completion-capable and `numBatchAuto` (user-set batch is never overridden). CUDA without flash attention short-circuits to 512 (256 on ≤8 GiB cards with big context) because KV/batch memory behaves differently there. Otherwise start from the context tier and walk DOWN while either the 80%-of-available check fails, the tier headroom gate fails, or `predictedVRAM + surcharge` exceeds `threshold - predicted`. The surcharge must be included in the preflight prediction too (`generationBatchSurchargeForCompletion`) or the fit check lies by up to 2 GiB.
**Invariant:** Never raise above the context-tier default; never touch an explicit user NumBatch; the same surcharge figure appears in both the preflight prediction (`predictedForLoad`) and the fit loop so decisions stay consistent.
**Probe:** `grep -cF "llamaServerGenerationBatchLarge       = 2048" server/sched.go` → `1`; `grep -c "2 * format.GibiByte" server/sched.go` → `1`. Direct tests: `TestSchedLoadOOMReducesAutomaticContextBeforeRetry` + full `go test ./server/ -run TestSched` battery (PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "automaticGenerationBatch NumBatch headroom", limit: 5 });
```

## Verdict
Adopt the tier ladder with downward-only adaptation plus the explicit surcharge-in-prediction trick. Adapt tier values/headroom percentages to your engine's batch-memory curve; omit the flash-attention CUDA special case when your runtime always has FA enabled.
