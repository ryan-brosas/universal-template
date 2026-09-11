<!-- capsule-v2 -->
# Stream-text event ledger — how do you reduce an open-ended chunk stream into per-step content snapshots that survive out-of-order and adversarial ids?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** How does the eventProcessor accumulate text/reasoning/tool parts into `StepResult.content`, and which bookkeeping rules stop a porter from corrupting step history?

## The eventProcessor transform (forward-then-record)
**Path/Symbol:** `packages/ai/src/generate-text/stream-text.ts:eventProcessor` (1187–1495): TransformStream built in the `DefaultStreamTextResult` constructor, piped AFTER `createOutputTransformStream` (:1590–1592).
**Signature:** `TransformStream<EnrichedStreamPart, EnrichedStreamPart>` whose `transform(chunk, controller)` FIRST does `controller.enqueue(chunk)` then updates ledger state; `flush(controller)` finalizes promises and fires `onEnd`.
**Data Shape:** ledger fields — `recordedContent: Array<ContentPart>` (per-step), `activeTextContent` / `activeReasoningContent: Record<string, {type, text, providerMetadata}>` keyed by provider chunk id via `createIdMap()`, `recordedSteps: StepResult[]`, `stepMessagesForNextStep`, `initialResponseMessages`.

### Decisive source
```ts
async transform(chunk, controller) {
  controller.enqueue(chunk); // forward the chunk to the next stream

  const { part } = chunk;
  await onChunk?.({ chunk: part });
  ...
  if (part.type === 'start-step') {
    // reset the recorded data when a new step starts:
    recordedContent = [];
    activeReasoningContent = createIdMap();
    activeTextContent = createIdMap();
    recordedRequest = part.request;
    recordedWarnings = part.warnings;
  }
```
(stream-text.ts:1191–1196, 1331–1339, verbatim)

```ts
if (part.type === 'text-delta') {
  const activeText = activeTextContent[part.id];
  if (activeText == null) {
    controller.enqueue({
      part: { type: 'error', error: `text part ${part.id} not found` },
      partialOutput: undefined,
    });
    return;
  }
  activeText.text += part.text;
```
(:1229–1243)

**Flow:** forward immediately → dispatch by `part.type`: `custom|source|tool-call|tool-approval-*|tool-error` push onto `recordedContent`; `text-start`/`reasoning-start` open an id-keyed accumulator AND push its BY-REFERENCE object into `recordedContent`; deltas append into the live object (mutation is what fills the snapshot); `-end` closes it → `tool-result` records ONLY if `!part.preliminary` → `finish-step` builds `DefaultStepResult` from the accumulated arrays and pushes to `recordedSteps`.
**Invariant:** (1) Forward-BEFORE-process: consumer latency never gates ledger correctness, and `onChunk` sees raw order. (2) Accumulators are MUTATED IN PLACE inside `recordedContent` — cloning at start would leave steps with empty text; copying at end would need index surgery. (3) `preliminary` tool-results stream to consumers but NEVER enter history — recording them double-counts outputs in response messages. (4) `createIdMap()` gives prototype-less lookup: a delta arriving for an unknown/`__proto__` id enqueues an inline `error` part rather than crashing or silently appending to inherited keys.
**Probe:** `stream-text.test.ts:2428` ("should not read Object.prototype for missing text part ids" — expects `error: 'text part __proto__ not found'`), `:2468` reasoning twin; preliminary-exclusion pinned by tool-result suites (:2262–2270 source contract).

## finish-step snapshot + flush-time aggregation
**Path/Symbol:** `stream-text.ts` finish-step handler (1341–1395) + `flush` (1404–1494).
**Signature:** `finish-step` → `toResponseMessages({content: recordedContent, tools})` → `new DefaultStepResult({...})` → `notify([onStepFinish, telemetry.onStepEnd])` → `stepFinish.resolve()`; `flush` → resolve `_finishReason/_rawFinishReason/_totalUsage/_steps`, flatMap aggregates, fire `onEnd`.
**Data Shape:** `onEnd` event carries cross-step flatMaps (`content/files/sources/toolCalls/toolResults/warnings`) plus `responseMessages: [...initialResponseMessages, ...steps.flatMap(s => s.response.messages)]` and both `finalStep` and `steps`.
**Decisive invariant:** `recordedRequestMessages` captured at step start is cloned into the step request ONLY when `include.requestMessages` (:1362–1367) — large media payloads stay out of memory unless opted in. Empty-history or `NoOutputGeneratedError` runs REJECT all result promises (`rejectResultPromises`, :1408–1419) instead of resolving with zero steps — consumers get an exception, not a fake empty completion.
**Probe:** `stream-text.test.ts` multi-step stitching assertions (stitchable-stream suites) and no-output rejection cases; timeout ladder interplay in `stream-text-timeout.test.ts:215`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "eventProcessor recordedContent finish-step", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "ai", query: "createIdMap prototype pollution stream", limit: 10 });
```

## Verdict
Adopt forward-then-record ordering, by-reference accumulators inside recorded content, preliminary-result exclusion from history, prototype-less id maps with inline error parts, and reject-on-empty flush semantics. Adapt the content-part taxonomy to your host's chunk types (keep the exhaustive switch discipline). Omit telemetry dispatcher plumbing (host-specific). Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2; decisive ranges read at HEAD this session.
