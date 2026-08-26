<!-- capsule-v2 -->
# needsReload auto-value reconciliation — when must an already-loaded runner be reloaded instead of reused?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How do you decide "same model, same options" so identical requests reuse the runner while a real option change triggers exactly one reload?

## runnerRef.needsReload
**Path/Symbol:** `server/sched.go` (`needsReload` :1382-1431). **Signature:** `func (runner *runnerRef) needsReload(ctx context.Context, req *LlmRequest) bool`.
**Data Shape:** Compares adapter paths, projector paths, and full `api.Options.Runner` structs; carries per-runner `numCtxAuto/numBatchAuto/useMMapAuto/contextShift/trainContext` flags recorded at load time. Ping timeout 10s normally, 2min while `runner.loading` (initial load of big models on slow disks).

### Decisive source
```go
optsExisting := runner.Options.Runner
optsNew := req.opts.Runner
optsNew.NumCtx = effectiveContext(optsNew.NumCtx, runner.trainContext) // clamp to train ctx
if runner.numCtxAuto && req.numCtxAuto   { optsNew.NumCtx   = optsExisting.NumCtx   } // both auto → equal by fiat
if runner.numBatchAuto && req.numBatchAuto { optsNew.NumBatch = optsExisting.NumBatch }
if runner.useMMapAuto && optsNew.UseMMap == nil { optsNew.UseMMap = optsExisting.UseMMap }
if optsNew.NumGPU < 0 { optsExisting.NumGPU = -1; optsNew.NumGPU = -1 }                // -1 = all layers
...
if !reflect.DeepEqual(runner.model.AdapterPaths, req.model.AdapterPaths) ||
   !reflect.DeepEqual(runner.model.ProjectorPaths, req.model.ProjectorPaths) ||
   (!runner.model.IsMLX() && !reflect.DeepEqual(optsExisting, optsNew)) ||
   runner.llama.Ping(ctx) != nil {
    return true
}
```

**Flow:** Effective-context clamp first (so a 4096-train-ctx model doesn't reload because someone asked for 8192 — llama-server already capped it), then each scheduler-AUTO field is normalized to the loaded value when BOTH sides are auto (auto defaults drift as free memory changes; treating them as differences would cause reload ping-pong), then deep-compare + liveness ping. Any mismatch ⇒ caller marks this runner for eviction and the pending request loads fresh.
**Invariant:** Only user-explicit values may force a reload; auto-vs-auto never compares unequal; a dead server (ping fail) is treated as an options change. MLX runners skip option comparison (their client holds no Options echo).
**Probe:** `grep -cF "runner.numCtxAuto && req.numCtxAuto" server/sched.go` → `1`. Direct test: `server/sched_test.go` suite exercises reuse vs reload via fake servers (`go test ./server/ -run TestSched` PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "needsReload runner options DeepEqual", limit: 5 });
```

## Verdict
Adopt auto-flag normalization before structural comparison and the loading-aware ping timeout. Adapt which options participate in equality to your engine's restart cost; omit the MLX carve-out if you have no second runner type.
