<!-- capsule-v2 -->
# otel callId state machine — how does a telemetry integration reconstruct a span tree from flat per-part events?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** How do you turn the Telemetry interface's unrelated event callbacks (`onStart`, `onStepStart`, `onLanguageModelCallStart/End`, `onToolExecutionStart/End`, `onEmbedStart/End`, `onRerankStart/End`, `onEnd`, `onAbort`, `onError`) into ONE coherent parent→child span hierarchy?

## Path/Symbol
`packages/otel/src/open-telemetry.ts:OpenTelemetry` (:110) — private `callStates = new Map<string, CallState>()` (:111), `getCallState` (:123), `cleanupCallState` (:127); `interface CallState` (:71–90).

**Signature:** every handler takes an event carrying `callId`; all span lookups go through `this.getCallState(event.callId)` and bail silently when absent (`if (!state?.rootSpan || !state.rootContext) return;`).

**Data Shape:** one `CallState` holds the whole tree's handles — `rootSpan/rootContext`, `stepSpan/stepContext`, `inferenceSpan/inferenceContext` (single slot, overwritten per step), `toolSpans: Map<toolCallId, {span, context}>`, `embedSpans: Map<embedCallId, …>` (multi-instance), `rerankSpan` (single), plus replayed settings (`settings`, `provider`, `modelId`, `baseSupplementalAttributes`, `objectSystemInstructions`) because step events don't re-carry them.

### Decisive source
```ts
    const rootSpan = this.tracer.startSpan(spanName, {
      attributes: this.getSpanAttributes({
        attributes,
        spanType: 'operation',
        operationId: event.operationId,
        callId: event.callId,
        runtimeContext,
      }),
      kind: SpanKind.INTERNAL,
    });
    const rootContext = trace.setSpan(context.active(), rootSpan);

    this.callStates.set(event.callId, {
```
(:307–319; `callStates.set` appears exactly 4× — generate :319, object :425, embed :621, rerank :1301)

**Flow:** `onStart` routes by `event.operationId` (embed/embedMany → embed start :210, rerank :217, generateObject/streamObject :225, else generate :234). Root span name = `` `${operationName} ${event.modelId}` `` (:306/:412/:608). Each child span is created under its parent's *context* explicitly: step under `rootContext` (:676), chat under `stepContext` (:746), tool under `parentContext = stepContext ?? rootContext` (:915), provider-tool under `inferenceContext` (:884). Ends clear their slot AND set it to `undefined` (`state.inferenceSpan.end(); state.inferenceSpan = undefined; state.inferenceContext = undefined;` :907–909); only operation end/abort/error calls `cleanupCallState` (:1098/:1141/:1177/:1326/:1424/:1471).

**Invariant:** (1) The map IS the tree — OTel parentage is passed via explicit context args, never ambient `startActiveSpan`, so async generator yields can't detach children; a porter who switches to active-span style breaks parenting across stream suspension. (2) Missing state is ALWAYS a silent no-op (`return`), never a throw — late/duplicate events after cleanup are dropped by design. (3) Settings captured at Start are REPLAYED from state at step/chat time (:693–709 reads `state.settings.temperature` etc.) because `LanguageModelCallStartEvent` doesn't re-carry sampling params — porting must keep this cache or lose request attributes on inference spans. (4) Single-slot inference/step fields vs Map-based tool/embed fields is load-bearing: steps are sequential, tools/embeds can interleave.

**Probe:** `grep -c "callStates.set" packages/otel/src/open-telemetry.ts` → 4 (anchored at repo root; one per operation family). `grep -n "inferenceContext ?? state?.stepContext" packages/otel/src/open-telemetry.ts` → :193 (model-call fallback order).

**Retrieve:** live-resolved rank-1 @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "OpenTelemetry callStates executeLanguageModelCall", limit: 5 });
// → packages/otel/src/open-telemetry.ts 185-200 OpenTelemetry.executeLanguageModelCall
```

**Verdict:** ADOPT whole. This is the reference design for event-driven tracing of any multi-step agent loop.
