<!-- capsule-v2 -->
# Streaming layer — how do you bound, smooth, stitch, and terminate a multi-step streaming model loop without wedging consumers?

**Source:** Vercel AI SDK (Apache-2.0) `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What are the portable contracts for loop termination, per-step preparation, stream smoothing, timeout layering, and step stitching — and which invariants does a porter get wrong?

## Stop conditions: predicate arrays replace max-steps
**Path/Symbol:** `packages/ai/src/generate-text/stop-condition.ts:isStopConditionMet` (64–77) + built-ins `isStepCount` (27–29), `isLoopFinished` (37–39), `hasToolCall` (47–54).
**Signature:** `StopCondition<TOOLS> = ({steps: StepResult[]}) => boolean | PromiseLike<boolean>`; evaluation `(await Promise.all(conditions.map(c => c({steps})))).some(Boolean)`.
**Data Shape:** conditions receive the ACCUMULATED step array; the natural terminations (finish reason ≠ `tool-calls`, tool without execute, tool call needs approval) live in the LOOP, not in any condition.

### Decisive source
```ts
export function isStepCount(stepCount: number): StopCondition<any, any> {
  return ({ steps }) => steps.length === stepCount;
}
```
```ts
return (
  await Promise.all(stopConditions.map(condition => condition({ steps })))
).some(result => result);
```
(`stop-condition.ts:27–29, 74–76`, verbatim; default `stopWhen = isStepCount(1)` at `stream-text.ts:376`, normalized via `asArray` at :806)

**Flow:** each step completes → all predicates evaluated against full history → ANY true stops the loop. `isLoopFinished()` is literally `() => false` (natural termination only); `hasToolCall(...names)` checks only the LAST step's `toolCalls`.
**Invariant:** predicates are pure functions of accumulated `StepResult`s — a porter who makes them stateful or side-effecting breaks composition (`Promise.all` runs them concurrently). Max-steps is one predicate among many, never a special counter.
**Probe:** `packages/ai/src/generate-text/stop-condition.test.ts` :22 exact-match semantics, :69 earlier-step tool calls don't count, :124 any-true short-circuit, :154 rejection propagates.

## prepareStep: per-step override of everything
**Path/Symbol:** `packages/ai/src/generate-text/stream-text.ts` — option declared :527, invoked :1931–2020.
**Signature:** `prepareStep({model, steps, stepNumber, instructions, toolsContext, runtimeContext, experimental_sandbox}) → {model?, messages?, instructions?|system?, activeTools?, toolChoice?, toolOrder?, providerOptions?, runtimeContext?, toolsContext?, experimental_sandbox?, ...callSettings} | undefined`.
**Data Shape:** every returned field replaces that step's value (`??` fallback to the run-level value); `runtimeContext`/`toolsContext` REPLACEMENTS become the base for subsequent steps (:1948–1949).

### Decisive source
```ts
const stepModel = resolveLanguageModel(prepareStepResult?.model ?? model);
const stepActiveTools = filterActiveTools({
  tools,
  activeTools: prepareStepResult?.activeTools ?? activeTools,
});
```
(`stream-text.ts:1951–1958`, verbatim; runtime-context mutation guidance at docstring :473)

**Flow:** before each step → prepareStep called with accumulated state → its result overrides model/tools/messages/settings for THIS step → step executes → next prepareStep sees the mutated context.
**Invariant:** overrides are per-step, but context mutations PERSIST across steps — "swap to a cheaper model after step 2" and "narrow the toolset each step" are both just prepareStep policies. A porter returning partial objects must keep the `??` fallbacks or unset fields crash resolution.
**Probe:** `stream-text.test.ts` multi-step suites exercise model/tool switching via prepareStep results (:7767 region pins settings propagation through start events).

## smoothStream: buffer + chunk detector + fixed-delay drain
**Path/Symbol:** `packages/ai/src/generate-text/smooth-stream.ts:smoothStream` (30–163).
**Signature:** `smoothStream({delayInMs = 10 | null, chunking = 'word' | 'line' | RegExp | ChunkDetector | Intl.Segmenter, _internal?: {delay}})(opts) => TransformStream<TextStreamPart, TextStreamPart>`.
**Data Shape:** buffers only `text-delta`/`reasoning-delta` chunks keyed by (type,id); everything else is a flush boundary then passes through untouched.

### Decisive source
```ts
// Flush buffer when type or id changes
if ((chunk.type !== type || chunk.id !== id) && buffer.length > 0) {
  flushBuffer(controller);
}
buffer += chunk.text;
...
if (chunk.providerMetadata != null) {
  providerMetadata = chunk.providerMetadata;
}
let match;
while ((match = detectChunk(buffer)) != null) {
  controller.enqueue({ type, text: match, id });
  buffer = buffer.slice(match.length);
  await delay(delayInMs);
}
```
```ts
if (!buffer.startsWith(match)) {
  throw new Error(
    `Chunking function must return a match that is a prefix of the buffer.`);
}
```
(`smooth-stream.ts:139–159, 74–78`, verbatim; regex detectors return `slice(0, match.index) + match[0]` so pre-match text drains first :104; Segmenter duck-typed by `'segment' in chunking` :49–61)

**Flow:** delta arrives → type/id change flushes old buffer → append → drain detected chunks one delay apart → non-delta chunk (tool call etc.) flushes then enqueues immediately.
**Invariant:** custom detectors MUST return a PREFIX of the buffer (or empty/null); `providerMetadata` (e.g. Anthropic thinking signatures) is captured from buffered chunks and re-emitted on the NEXT flush — dropping it corrupts signed reasoning streams.
**Probe:** `smooth-stream.test.ts` (34 cases) :766/:748 prefix/empty-match throws, :216 buffer flushed before tool-call starts, :407 no whitespace-only chunks, :787 default 10ms delay.

## Four-layer timeout ladder + signal merging
**Path/Symbol:** `packages/ai/src/prompt/request-options.ts:TimeoutConfiguration` (13–22, getters 30–98); `packages/ai/src/util/merge-abort-signals.ts:mergeAbortSignals` (13–25); armed in `stream-text.ts:751–786, 1827–1875`; enforced per-tool in `execute-tool-call.ts:120–122`.
**Signature:** `timeout?: number | {totalMs?, stepMs?, firstChunkMs?, chunkMs?, toolMs?, tools?: {\`${tool}Ms\`}}`; `mergeAbortSignals(...(AbortSignal | number | null | undefined)[]): AbortSignal | undefined`.
**Data Shape:** numbers become `AbortSignal.timeout(n)`; ≥2 valid sources merge via `AbortSignal.any`; zero valid → `undefined`.

### Decisive source
```ts
abortSignal: mergeAbortSignals(
  abortSignal,
  totalTimeoutMs,
  stepAbortController?.signal,
  firstChunkAbortController?.signal,
  chunkAbortController?.signal,
),
```
```ts
// The first-content timeout is armed when the provider response stream
// starts and is cleared by the first semantic output chunk.
```
(`stream-text.ts:778–784, 1835–1836`, verbatim; per-tool: `getToolTimeoutMs(timeout, toolName)` → `tools['${name}Ms'] ?? toolMs`, request-options.ts:89–98)

**Flow:** total aborts everything → step timer re-arms each step → firstChunk arms at stream start, cleared by FIRST SEMANTIC output chunk, re-armed next step → chunk timer resets on each semantic chunk only → each tool execution gets caller-signal + per-tool timeout merged.
**Invariant:** NON-semantic chunks (raw events) neither clear firstChunk nor reset chunk timeouts (`stream-text-timeout.test.ts:36` "only non-output chunks" aborts; :380 chunk not reset for non-output) — resetting on raw traffic lets dead providers stall forever under cover of keep-alives.
**Probe:** `stream-text-timeout.test.ts` :36 abort on non-output-only prefix, :215 re-arm per step, :293 clear on provider error, :327 clear on cancel; `stream-text.test.ts` :17252/:17457 total+step+chunk coexistence.

## Stitchable streams: N step-streams → one observable
**Path/Symbol:** `packages/ai/src/util/create-stitchable-stream.ts:createStitchableStream` (9–138).
**Signature:** `{stream, addStream(inner, callbacks?), close(), terminate()}`.
**Data Shape:** outer `ReadableStream` pulls from an ordered queue of inner readers; `addStream` after `close()` throws.

### Decisive source
```ts
if (innerStreams.length === 0) {
  waitForNewStream = createResolvablePromise<void>();
  await waitForNewStream.promise;
  return await processPull();
}
```
```ts
} catch (error) {
  currentStream.onError?.(error);
  controller?.error(error);
  innerStreams.shift();
  terminate(); // we have errored, terminate all streams
}
```
(`create-stitchable-stream.ts:51–55, 77–83`, verbatim)

**Flow:** pull waits on a resolvable promise when no inner stream is queued → `addStream` resolves it → current stream drained to done → shift to next → `close()` ends gracefully AFTER queued streams finish; `terminate()` cancels all immediately.
**Invariant:** the pull loop BLOCKS (not polls, not errors) between steps — multi-step runs stay one unbroken consumer stream while each `StepResult` remains available separately. An inner-stream error fails the WHOLE outer stream and terminates siblings (no silent skip).
**Probe:** exercised indirectly by multi-step `stream-text.test.ts` stitching assertions; no dedicated unit file — port with your own backpressure/error test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", name_pattern: "^(isStopConditionMet|hasToolCall|smoothStream|createStitchableStream|mergeAbortSignals)$", detail: "ids" });
await mcp.codebase_memory.search_graph({ project: "ai", query: "firstChunk timeout semantic output", limit: 10 });
```

## Verdict
Adopt predicate-array termination, per-step override-with-fallback preparation, prefix-contract smoothing with metadata carry-through, the four-layer timeout ladder over merged abort signals, and pull-blocking stitchable streams. Adapt timeout defaults, chunk regexps/delay, and step-count policy to host UX. Omit the RSC/UI stream protocol layers unless a target renders chat UIs. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2 — decisive ranges read at HEAD this session.
