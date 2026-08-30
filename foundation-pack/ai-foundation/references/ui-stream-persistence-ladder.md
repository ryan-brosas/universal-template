<!-- capsule-v2 -->
# Server-side persistence ladder — how does the SERVER run the client reducer over its own outgoing stream to fire onEnd/onStepEnd exactly once, even when the browser walks away?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you get persistence-grade callbacks (final message, continuation flag, abort flag) out of a chunk stream you are simultaneously forwarding to a client?

## handleUIMessageStreamFinish
**Path/Symbol:** `packages/ai/src/ui-message-stream/handle-ui-message-stream-finish.ts:handleUIMessageStreamFinish` (:14-189 whole); reuses `createStreamingUIMessageState`/`processUIMessageStream` from the CLIENT reducer (`../ui/process-ui-message-stream`, capsule ui-chunk-reducer).
**Signature:** `({stream, messageId?, originalMessages?, onError, onStepEnd?/onStepFinish?, onEnd?/onFinish?}): ReadableStream<InferUIMessageChunk>`.

### Decisive source
```ts
let lastMessage = originalMessages?.[originalMessages.length - 1];
if (lastMessage?.role !== 'assistant') lastMessage = undefined;
else { messageId = lastMessage.id; }              // CONTINUATION: server forces the same id

const idInjectedStream = stream.pipeThrough(new TransformStream({ transform(chunk, controller) {
  if (chunk.type === 'start' && startChunk.messageId == null && messageId != null)
    startChunk.messageId = messageId;             // id injected INTO THE WIRE CHUNK
  if (chunk.type === 'abort') isAborted = true;   // flag captured in pass-through mode too
  controller.enqueue(chunk);
}}));

// Only process the stream if we need to track state for callbacks
if (resolvedOnEnd == null && resolvedOnStepEnd == null) return idInjectedStream;   // ZERO-cost passthrough

// onStepEnd gets DEEP CLONES so persistence callbacks can't mutate live state:
await resolvedOnStepEnd({ isContinuation,
  responseMessage: structuredClone(state.message), messages: [...origTail, structuredClone(state.message)] });

// terminal delivery — BOTH stream endings:
async cancel() { await callOnEnd(); }   // reader.cancel() = user navigated away mid-stream (@ts-expect-error: cancel still missing from TS types)
async flush()  { await callOnEnd(); }
// callOnEnd: finishCalled latch ⇒ exactly once; isContinuation = state.message.id === lastMessage?.id;
// messages array REPLACES the continued tail with the final responseMessage.
```

**Flow:** chunks pass through id-injection (mutating the start chunk before forwarding), then EITHER return untouched (no callbacks configured) OR flow through the full reducer state machine; `finish-step` chunks await `callOnStepFinish` inline (backpressure-coupled ordering); flush and cancel both funnel into the latched `callOnEnd`.
**Invariant:** (1) The no-callback early return (:99-101) means the reducer only runs when someone persists — a pure proxy pays nothing. (2) Continuation is decided by ID EQUALITY against the last ASSISTANT original message (`isContinuation = state.message.id === lastMessage?.id`; test :176 vs :221 'should not treat user message as continuation'); the messages array handed to onEnd splices out the old tail so persisters never double-store it. (3) `isAborted` is set by OBSERVING an abort chunk in the injection transform — it works even in pass-through mode where the reducer never runs (tests :370/:395). (4) onStepEnd receives structuredCloned snapshots (:150/:155; test :713 'deep-cloned messages … to prevent mutation') but onEnd receives the LIVE state.message — cloning there would be wasted work at terminal. (5) onStepEnd errors are logged via onError and swallowed (:158-160; test :630 'logging and continuing') — persistence failures must not break the client stream. (6) cancel+flush BOTH call callOnEnd because a cancelled TransformStream never flushes; the latch makes double-fire impossible (test :425 'when reader is cancelled (simulating browser close/navigation)'). Porters who deliver onFinish only in flush lose the callback on every client disconnect.

**Probe:** `bash -c "grep -n '@ts-expect-error cancel is still new' /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/handle-ui-message-stream-finish.ts && grep -n 'simulating browser close' /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/handle-ui-message-stream-finish.test.ts && grep -c structuredClone /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/handle-ui-message-stream-finish.ts"` → `:179`, `:425`, `3`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createUIMessageStream handleUIMessageStreamFinish toUIMessageChunk", limit: 5 });
// → ai.packages.ai.src.ui-message-stream.handle-ui-message-stream-finish.handleUIMessageStreamFinish Function :14-189
```

## Verdict
Adopt id-injection-at-start, the zero-cost passthrough gate, clone-for-step/live-for-end split, and the cancel-or-flush exactly-once terminal latch. Adapt the callback payload to your storage layer. Omit the step-callback plumbing if you have no intermediate-persistence requirement.
