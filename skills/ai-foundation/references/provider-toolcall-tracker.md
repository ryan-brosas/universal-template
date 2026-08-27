<!-- capsule-v2 -->
# Provider streaming tool-call tracker — how do OpenAI-compatible argument deltas become complete tool calls without ever acting on a parsable prefix?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How are streaming tool-call deltas keyed, accumulated, and finalized — and why must finalization wait for stream flush?

## StreamingToolCallTracker
**Path/Symbol:** `packages/provider-utils/src/streaming-tool-call-tracker.ts:StreamingToolCallTracker` (:77-252), `processDelta` (:110-129), `flush` (:135-141).
**Signature:** `new StreamingToolCallTracker(controller: Pick<TransformStreamDefaultController<LanguageModelV4StreamPart>,'enqueue'>, options?: {generateId?, typeValidation?: 'none'|'if-present'|'required', extractMetadata?, buildToolCallProviderMetadata?})`; `processDelta(delta): void`; `flush(): void`. Used by openai, openai-compatible, groq, deepseek, and alibaba providers (source comment :69-76).
**Data Shape:** Delta = `{index?, id?, type?, function?: {name?, arguments?}}` with ALL fields nullable. Internal state: `toolCalls: Set`, `toolCallsById: Map`, `toolCallsByIndex: Map<number>`, `latestToolCall`. Emits `tool-input-start` / `tool-input-delta` / `tool-input-end` / `tool-call` parts.

### Decisive source
```ts
processDelta(toolCallDelta) {
  const { id, index } = toolCallDelta;
  let toolCall =
    id != null && id.length > 0 ? this.toolCallsById.get(id)      // 1. non-empty id wins
    : index != null              ? this.toolCallsByIndex.get(index) // 2. else index
    :                              this.latestToolCall;            // 3. else latest
  if (toolCall == null) toolCall = this.processNewToolCall(toolCallDelta);
  else                  this.processExistingToolCall(toolCall, toolCallDelta);
  if (index != null) this.toolCallsByIndex.set(index, toolCall);   // index re-binding
  this.latestToolCall = toolCall;
}
// processExistingToolCall:
if (toolCall.hasFinished) return;                       // late deltas silently dropped
if (toolCallDelta.function?.arguments != null) {
  toolCall.function.arguments += toolCallDelta.function.arguments;
  this.controller.enqueue({ type: 'tool-input-delta', id: toolCall.id,
    delta: toolCallDelta.function.arguments });
}
```
```ts
// Tool calls must not finalize before the stream ends: a parsable
// argument buffer can still be the prefix of a longer argument string,
// so acting on it early would use truncated inputs (see #13137).
// Finalization happens in flush().
```

**Flow:** resolve existing call via id → index → latest ladder; new call ⇒ three validations (`type` per mode, non-null `id`, non-null `function.name`) then enqueue `tool-input-start` (+ immediate delta if the FIRST chunk already carried arguments) → continuation deltas append and re-emit → `flush()` finalizes every unfinished call: `tool-input-end` then `tool-call {toolCallId: id ?? generateId(), toolName, input: fullArguments, providerMetadata?}`.
**Invariant:** NO early finalization even when the accumulated buffer is valid JSON (#13137 — a parsable buffer may still be the strict prefix of a longer one). Index reuse after a finished call creates a NEW tracked call (test :212 "keep distinct tool calls that reuse an index"); empty-string ids never enter the id map but still track by index/latest. `typeValidation:'required'` throws on any non-'function' type; `'if-present'` only when present; `'none'` (default) ignores it.
**Probe:** `packages/provider-utils/src/streaming-tool-call-tracker.test.ts:118` (parsable prefix not finalized before flush), `:212` (index reuse = distinct calls), `:278` (empty continuation ids fall back to index), `:308` (finished calls skip deltas), `:356` (missing index continues latest), `:506` (no double finalize on flush).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"StreamingToolCallTracker processDelta flush tool-input-start","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the resolution ladder, the flush-time-only finalization rule, and the index-reuse-creates-new-call semantics verbatim; adapt `typeValidation`/metadata hooks per provider dialect; omit the V4-specific stream-part shapes. This is the provider-side TWIN of the ai-package parse/repair ladder capsule — port them together or the wire boundary leaks truncated inputs.
