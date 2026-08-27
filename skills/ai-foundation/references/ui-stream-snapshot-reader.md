<!-- capsule-v2 -->
# Chunk-stream → message snapshot reader — how does a consumer turn UIMessageChunks into per-write message states without cloning megabytes of accumulated text?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you expose "the message so far" as a stream of immutable snapshots cheaply, and what exactly happens when the chunk stream itself contains an error?

## readUIMessageStream + createUIMessageSnapshot
**Path/Symbol:** `packages/ai/src/ui-message-stream/read-ui-message-stream.ts:readUIMessageStream` (:55-117 whole) + module helper `createUIMessageSnapshot` (:15-42).
**Signature:** `({message?, stream: ReadableStream<UIMessageChunk>, onError?, terminateOnError=false}): AsyncIterableStream<UI_MESSAGE>`.

### Decisive source
```ts
function createUIMessageSnapshot(message) {
  const textByPartIndex = new Map();
  const messageWithoutText = { ...message, parts: message.parts.map((part, index) => {
    if (part.type === 'text' || part.type === 'reasoning') {
      textByPartIndex.set(index, part.text);
      return { ...part, text: '' };        // STRIP accumulated strings before cloning
    }
    return part;
  })};
  const snapshot = structuredClone(messageWithoutText);
  for (const [index, text] of textByPartIndex) snapshot.parts[index].text = text;   // reattach by INDEX
  return snapshot;
}
// write callback inside processUIMessageStream:
write: () => { controller?.enqueue(createUIMessageSnapshot(state.message)); }
// close guard:
}).finally(() => { if (!hasErrored) controller?.close(); });
//   — comment :109-110: calling close() on an errored controller throws "Invalid state" TypeError.
```

**Flow:** the SAME reducer kernel as the client (pass 7) and the server persistence ladder (handle-ui-message-stream-finish) folds chunks into one evolving state; every reducer `write` enqueues a fresh SNAPSHOT of the message; consumers iterate `for await (const msg of readUIMessageStream(...))` getting progressive renders.
**Invariant:** (1) Text/reasoning bodies are lifted OUT of the object before structuredClone and reattached by part index afterward (:18-39) — structuredClone copies strings by value, so cloning a long streaming message on every token would be O(n²) in bytes; tests pin both the exclusion (:241 'should exclude accumulated text from structured cloning') and that independent snapshots stay isolated from each other AND from inputs (:170/:290). (2) Snapshots are emitted at REDUCER WRITE POINTS, not on a timer — frequency follows chunk cadence. (3) Error handling is dual-mode: `terminateOnError:false` (default) reports via onError and keeps streaming snapshots; `terminateOnError:true` errors the OUTPUT stream ONCE (`hasErrored` latch prevents erroring twice; test :359 'should throw an error when encountering an error UI stream part'). (4) The finally-close is guarded by `hasErrored` because closing after controller.error() throws TypeError (:108-114) — the same suppress-class discipline as the writer kernel's safeEnqueue. Porters who naive-clone per delta leak O(n²) allocations; porters who close-after-error throw on every aborted render.

**Probe:** `bash -c "grep -c textByPartIndex /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/read-ui-message-stream.ts && grep -n 'exclude accumulated text from structured cloning' /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/read-ui-message-stream.test.ts && grep -n 'already closed' /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui-message-stream/read-ui-message-stream.ts"` → `3`, `:241`, `:110`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "readUIMessageStream uiMessageChunkSchema getResponseUIMessageId JsonToSseTransformStream createAgentUIStream", limit: 5 });
// → ai.packages.ai.src.ui-message-stream.read-ui-message-stream.readUIMessageStream Function :55-117
```

## Verdict
Adopt strip-before-clone snapshotting keyed by part index, write-point emission, and the errored-controller close guard. Adapt snapshot granularity to your UI's render budget. Omit terminateOnError if your consumer treats error chunks as data.
