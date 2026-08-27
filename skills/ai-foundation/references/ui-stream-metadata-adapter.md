<!-- capsule-v2 -->
# streamText → UI stream adapter — where does per-part metadata ride, and why do start/finish get it inline while every other part gets a second chunk?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you enrich an event stream with caller metadata (tokens, latency) without inventing new chunk types or duplicating metadata on lifecycle frames?

## toUIMessageStream
**Path/Symbol:** `packages/ai/src/ui-message-stream/to-ui-message-stream.ts:toUIMessageStream` (:18-91 whole); id resolution `get-response-ui-message-id.ts:getResponseUIMessageId` (:15-35).
**Signature:** `({stream: ReadableStream<TextStreamPart>, tools?, sendReasoning?, sendSources?, sendStart?, sendFinish?, onError?, messageMetadata?: (part) => METADATA|Promise, originalMessages?, generateMessageId?, onEnd?/onFinish?}): ReadableStream<InferUIMessageChunk>`.

### Decisive source
```ts
transform: async (part, controller) => {
  const messageMetadataValue = messageMetadata?.({ part });   // PER PART — recomputed for every chunk
  const uiMessageChunk = toUIMessageChunk(part, { ..., messageMetadata: messageMetadataValue, responseMessageId });
  if (uiMessageChunk != null) controller.enqueue(uiMessageChunk);
  // start and finish events already include metadata in the converted
  // chunk; for other part types emit a separate message-metadata chunk
  if (messageMetadataValue != null && part.type !== 'start' && part.type !== 'finish') {
    controller.enqueue({ type: 'message-metadata', messageMetadata: messageMetadataValue });
  }
},
```
```ts
// get-response-ui-message-id.ts — the continuation ladder:
if (originalMessages == null) return undefined;              // no persistence ⇒ client owns ids
return lastMessage?.role === 'assistant'
  ? lastMessage.id                                            // CONTINUATION reuses the assistant id
  : typeof responseMessageId === 'function' ? responseMessageId() : responseMessageId;
```

**Flow:** TextStreamParts pipe through this TransformStream one-by-one; each part gets a fresh `messageMetadata` callback invocation, then conversion; non-lifecycle parts with metadata emit a FOLLOW-UP `message-metadata` chunk. The composed stream then flows into `handleUIMessageStreamFinish` with `messageId = responseMessageId ?? generateMessageId?.()` and `onEnd ?? onFinish`.
**Invariant:** (1) The dual-channel metadata rule exists because the wire contract has BOTH shapes — `start`/`finish` chunks carry an optional `messageMetadata` field, while mid-stream parts don't; emitting a separate `message-metadata` chunk after a start would double-write the same value on the reducer (test :158 'emits separate metadata chunks for non-lifecycle parts'). Porters who attach metadata ONLY to lifecycle parts silently lose token counts emitted mid-stream. (2) Metadata is computed per-part, not once — the callback sees every part so it can react to usage deltas arriving on finish-delta-like events; memoizing the first call changes semantics for callers deriving values from late parts. (3) Continuation identity is decided HERE via last-assistant-id reuse (`getResponseUIMessageId.test.ts`:16/:28/:40 cover null/originals/user-tail branches); when `originalMessages == null`, returning undefined is what makes handleUIMessageStreamFinish skip injection — non-persistence mode never fabricates server ids. (4) `sendReasoning/sendSources/sendStart/sendFinish` pass through untouched as converter gates — this layer adds no filtering of its own.

**Probe:** `bash -c "grep -n \"part.type !== 'start'\" /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/to-ui-message-stream.ts && grep -n 'emits separate metadata chunks for non-lifecycle parts' /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/to-ui-message-stream.test.ts"` → `:72` and `:158`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "readUIMessageStream uiMessageChunkSchema getResponseUIMessageId JsonToSseTransformStream createAgentUIStream", limit: 5 });
// → ai.packages.ai.src.ui-message-stream.get-response-ui-message-id.getResponseUIMessageId Function :15-35
```

## Verdict
Adopt per-part metadata computation plus the lifecycle-inline vs follow-up-chunk split. Adapt the metadata payload shape. Omit getResponseUIMessageId only if your protocol has no continuation concept.
