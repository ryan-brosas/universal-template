<!-- capsule-v2 -->
# UI message stream writer kernel — how does a server keep a chunk stream open for merges that arrive AFTER execute() returns, and how do errors cross it?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you build a server-side writer around a ReadableStream such that (a) merged sub-streams can be attached after the producer already returned, (b) producer errors become protocol chunks instead of rejected streams, and (c) enqueue-after-close never throws into user code?

## createUIMessageStream + UIMessageStreamWriter
**Path/Symbol:** `packages/ai/src/ui-message-stream/create-ui-message-stream.ts:createUIMessageStream` (:28-161 whole); writer interface `ui-message-stream/ui-message-stream-writer.ts:UIMessageStreamWriter` (24L: `write` / `merge` / `onError`).
**Signature:** `createUIMessageStream({execute({writer}), onError?, originalMessages?, onStepEnd?/deprecated onStepFinish, onEnd?/deprecated onFinish, generateId?}): ReadableStream<InferUIMessageChunk>`.

### Decisive source
```ts
const ongoingStreamPromises: Promise<void>[] = [];
// execute() runs SYNCHRONOUSLY here; its returned promise is pushed too:
writer.merge(streamArg) => ongoingStreamPromises.push(
  (async () => { /* read loop */ while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    safeEnqueue(value);          // every forwarded chunk
  }})().catch(error => safeEnqueue({ type: 'error', errorText: onError(error) })),
);
function safeEnqueue(data) { try { controller.enqueue(data); } catch {} }   // closed-stream writes suppressed

// liveness loop — re-checks the ARRAY, not a snapshot of it:
const waitForStreams = new Promise(async resolve => {
  while (ongoingStreamPromises.length > 0) { await ongoingStreamPromises.shift(); }
  resolve();
});
waitForStreams.finally(() => { try { controller.close(); } catch {} });
```

**Flow:** `execute` receives the writer and may return before any merged stream has data; each `merge` pushes an async read-loop promise onto the array; the drain loop keeps shifting promises until the array is momentarily empty, THEN closes. Because a later `merge` can push onto the array between shifts (the test attaches controller2 after execute returned and controller1 closed), close only happens when no merge ever follows.
**Invariant:** (1) The liveness check must RE-READ the shared array after every await — snapshotting "pending count at execute-return" would close mid-merge; this is what makes "forward new streams from callbacks" legal (`create-ui-message-stream.test.ts`:317 'should support writing from delayed merged streams' proves post-execute merge delivers). (2) EVERY error path funnels to `safeEnqueue({type:'error', errorText: onError(error)})` — sync throw in execute (:127-132), returned-promise rejection (:117-126), merged-substream rejection inside the read loop's `.catch`. Consumers never see an errored ReadableStream; they see an `error` CHUNK (tests :197/:252/:270). (3) `onError` DEFAULTS to `() => 'An error occurred.'` deliberately — server error details must not leak to clients; richer messages are opt-in (comment-pinned :30). (4) Writes after close are swallowed, never thrown (:82-88, test :288 'should suppress error when writing to closed stream'). (5) Deprecated aliases resolve `onStepFinish→onStepEnd`, `onFinish→onEnd` at the call site (:157-158). Porters who reject the stream on producer failure or who close eagerly at execute-return break both merge-late consumers and error-as-data clients.

**Probe:** `bash -c "grep -n 'should support writing from delayed merged streams' $REFERENCE_ROOT/ai/packages/ai/src/ui-message-stream/create-ui-message-stream.test.ts && grep -c safeEnqueue $REFERENCE_ROOT/ai/packages/ai/src/ui-message-stream/create-ui-message-stream.ts"` → `:317` and `6`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createUIMessageStream handleUIMessageStreamFinish toUIMessageChunk", limit: 5 });
// → ai.packages.ai.src.ui-message-stream.create-ui-message-stream.createUIMessageStream Function ... :28-161
```

## Verdict
Adopt the promise-array drain loop with re-read-before-close, the error-chunk funnel with detail-hiding default, and swallow-on-closed writes verbatim. Adapt chunk type names to your protocol. Omit `merge` if your host never composes sub-streams.
