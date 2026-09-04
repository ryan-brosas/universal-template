<!-- capsule-v2 -->
# CompletionStreamer transform split — why does the timeout killer wrap the raw LLM stream while display filters wrap the reused stream?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** Where exactly do "stop the LLM's generation" transforms and "truncate displayed text" filters each sit, and what must still work when a generator is REUSED from a previous keystroke?

## Two-layer streaming architecture
**Path/Symbol:** `core/autocomplete/generation/CompletionStreamer.ts:streamCompletionWithFilters` (:16-83) + `stopAfterMaxProcessingTime` (`generation/utils.ts`:1-27).
**Signature:** `streamCompletionWithFilters(token: AbortSignal, llm: ILLM, prefix: string, suffix: string, prompt: string, multiline: boolean, completionOptions?: Partial<CompletionOptions>, helper: HelperVars): AsyncGenerator<string>`; `stopAfterMaxProcessingTime(stream: AsyncGenerator<string>, maxTimeMs: number, fullStop: () => void): AsyncGenerator<string>`.
**Data Shape:** consumes `llm.streamFim(prefix, suffix, signal)` when `supportsFim()` else `llm.streamComplete(prompt, signal, {...opts, raw: true})`; yields string chunks; `fullStop` is `currentGenerator.cancel()`.

### Decisive source
```ts
// Full stop means to stop the LLM's generation, instead of just truncating the displayed completion
const fullStop = () => this.generatorReuseManager.currentGenerator?.cancel();

const generator = this.generatorReuseManager.getGenerator(prefix, (abortSignal) => {
  const generator = llm.supportsFim()
    ? llm.streamFim(prefix, suffix, abortSignal, completionOptions)
    : llm.streamComplete(prompt, abortSignal, { ...completionOptions, raw: true });
  /**
   * This transformer applies even on reused generator. We are deliberately
   * not using streamTransformPipeline because we want to capture and stop
   * the request even if the generator is being reused.
   */
  return helper.options.transform
    ? stopAfterMaxProcessingTime(generator, helper.options.modelTimeout * 2.5, fullStop)
    : generator;
}, multiline);
```
```ts
// utils.ts — check every 10 chunks to avoid performance overhead
const checkInterval = 10;
for await (const chunk of stream) {
  yield chunk;
  if (++chunkCount % checkInterval === 0 && Date.now() - startTime > maxTimeMs) {
    fullStop();
    return;
  }
}
```

**Flow:** factory closure passed into `GeneratorReuseManager.getGenerator` builds the FIM/complete stream → wraps it in `stopAfterMaxProcessingTime(modelTimeout × 2.5)` FIRST (inside reuse manager, so reused generators inherit it) → consumer-cancellation loop yields until the external `token.aborted` → THEN the display-side `StreamTransformPipeline.transform(initialGenerator, prefix, suffix, multiline, stopTokens, fullStop, helper)` wraps the fresh iteration only.
**Invariant:** The TIME-BASED killer must wrap the generator INSIDE the reuse manager (it travels with the reused underlying request); the TEXT-BASED filters stay OUTSIDE because a reused generator replays chunks already filtered under the OLD prefix. `fullStop` cancels the LLM request itself — display truncation alone leaves tokens billing. Time checks happen every 10 chunks, and chunks yielded BEFORE the deadline always pass through (an already-yielded chunk is never retracted).
**Probe:** `core/autocomplete/generation/utils.vitest.ts` — fast stream: `fullStop` NOT called (:37); long stream: outputs ≥10 chunks then `expect(fullStop).toHaveBeenCalled()` (:76-78) with Date.now spied ≤15 times (:100-101); empty output: `output === ""` and fullStop NOT called (:113-114).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "CompletionStreamer streamCompletionWithFilters stopAfterMaxProcessingTime", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer split (time-based cancel inside reuse, text-based filters outside) and the `modelTimeout × 2.5` ceiling with chunk-interval checking; adapt the multiplier to your cost model; omit Continue-specific `StreamTransformPipeline` internals (covered by `stream-filtering.md`). Direct tests pin `stopAfterMaxProcessingTime`; the split rationale is a load-bearing source comment (quoted verbatim above).
