<!-- capsule-v2 -->
# Harness result-object twin — how does a push-driven third-party runtime expose the exact `streamText()` consumer surface without running a language model?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Your driver emits events from a foreign runtime; consumers want `await result.text`, `result.fullStream`, `result.steps` in ANY order with streamText semantics — what does the adapter class owe them?

## DelayedPromise field-per-accessor + one settled latch

**Path/Symbol:** `packages/harness/src/agent/internal/harness-stream-text-result.ts` — `HarnessStreamTextResult` (:74–168), `abort` (:495–504), `fail` (:510–519), `rejectDelayedPromises` (:521–552), `teeStream` (:556–562).
**Signature:** `new HarnessStreamTextResult({ tools, runtimeContext, toolsContext, harnessId, sessionId, output })` implements `StreamTextResult<TOOLS, RUNTIME_CONTEXT, OUTPUT>`; driver methods `enqueue/enqueueContinuation/discardCurrentStepContent/finishStep/finish/abort/fail`.
**Data Shape:** 22 private `DelayedPromise<StreamProp<..., KEY>>` fields — each typed against the corresponding `StreamTextResult` property so the surface cannot drift from ai-core as it evolves.

### Decisive source
```ts
// :79–84 — per-accessor promises typed against StreamTextResult's own keys
private readonly _content = new DelayedPromise<
  StreamProp<TOOLS, RUNTIME_CONTEXT, OUTPUT, 'content'>
>();
...
// :495–503 — abort settles as a terminal PART for stream readers AND a rejection for awaiters
abort(input: { error: unknown; reason?: string }): void {
  if (this.settled) return;
  this.settled = true;
  this.fullStreamController.enqueue({ type: 'abort', ... } as TextStreamPart<TOOLS>);
  this.fullStreamController.close();
  this.rejectDelayedPromises(input.error);
}
// :546–550 — every promise rejects behind try/catch; double-rejection ignored
try { (dp as DelayedPromise<unknown>).reject(error); } catch { /* ignore double-rejection */ }
// :556–562 — tee-and-keep-remainder so every getter is an independent branch
private teeStream() {
  const [stream, remainingStream] = this.baseStream.tee();
  this.baseStream = remainingStream;
  return stream;
}
```

**Flow:** runPrompt constructs the result and pushes translated parts via the writer methods → stream readers consume terminal parts (`finish`/`error`/`abort`) while awaiting consumers read the delayed promises → abort/fail close the stream normally (no thrown read) but REJECT all promises so `await result.text` never hangs.
**Invariant:** One `settled` latch makes finish/abort/fail exactly-once and mutually exclusive; stream termination never throws, promise accessors never hang; `fullStream === stream` (same getter); un-awaited branches of the tee simply buffer.
**Probe:** deterministic content probes at pin: `HarnessStreamTextResult.abort` :495–504 enqueues `{type:'abort'}` then rejects promises (read-verified byte-exact); direct tests `run-prompt.test.ts:2011–2028` ("settles with an abort part instead of an error part…" — `parts.filter(error).length===0`, last part type `'abort'`, `result.finishReason` rejects) and `:2030–2051` (real error keeps an `error` part). No dedicated class test exists (see coverage caveat in ai-work/research.md pass 19).
**Retrieve:** `search_graph { project:"ai", query:"harness stream text result turn telemetry" }` → `HarnessStreamTextResult.stream/text/textStream/toTextStreamResponse…` all rank on file `harness-stream-text-result.ts` :564–806 (verified live @pin).

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ai", qualified_name: "ai.packages.harness.src.agent.internal.harness-stream-text-result.HarnessStreamTextResult.finish" });
```

## Verdict
Adopt the field-per-accessor DelayedPromise pattern + single settled latch + reject-all-on-terminal for any push-driven fake of a rich result API; adapt the property list to your host result interface; omit the tee bookkeeping if only one consumer exists.
