<!-- capsule-v2 -->
# smooth-stream chunking transform — how do you pace LLM text deltas into consistent word/line chunks without losing metadata or control chunks?

**Source:** mastra Apache-2.0 `main@3d2ff0d0a959792331f7cfb12dab6d08506676e7`; Codebase Memory `ext-mastra`. **Question:** How does a buffering TransformStream split provider text deltas on chunk boundaries (word/line/regex/Segmenter/custom), delay emission, and still flush pending metadata and trailing buffers correctly?

## Detector-driven buffer with metadata-carrying flush
**Path/Symbol:** `packages/core/src/stream/smooth-stream.ts` : `smoothStream` (:104-179) with `createChunkDetector` (:42-95) and `enqueueBufferedText` (:114-138).
**Signature:** `smoothStream<OUTPUT>({ delayInMs = 10 | null, chunking = 'word' | 'line' | RegExp | detector(buffer)=>string|null | Intl.Segmenter }): TransformStream<ChunkType, ChunkType>`.
**Data Shape:** buffers only `{type: 'text-delta'|'reasoning-delta'}` chunks; a single buffered chunk + string buffer + pending `metadata` + pending `payload.providerMetadata`. All other chunk types pass through untouched AFTER a full buffer flush.

### Decisive source
```typescript
const enqueueBufferedText = (controller, text) => {
  // Emit even when the text is empty if metadata is still pending, so a
  // trailing metadata-only delta (e.g. Gemini thought signatures, #20469)
  // is not silently dropped on flush.
  const hasPendingMetadata = bufferedMetadata !== undefined || bufferedProviderMetadata !== undefined;
  if (!bufferedChunk || (!text && !hasPendingMetadata)) return;
  // …enqueue { ...chunkWithoutMetadata, metadata?, payload: { …, providerMetadata?, text } }
  // metadata carried by the LATEST delta of the group; never duplicated across chunks.
};

async transform(chunk, controller) {
  if (chunk.type !== 'text-delta' && chunk.type !== 'reasoning-delta') { flushBuffer(controller); controller.enqueue(chunk); return; }
  if (bufferedChunk && (chunk.type !== bufferedChunk.type || chunk.payload.id !== bufferedChunk.payload.id)) flushBuffer(controller); // part-id boundary
  buffer += chunk.payload.text;
  bufferedMetadata = chunk.metadata ?? bufferedMetadata;
  let match;
  while ((match = detectChunk(buffer)) != null) {
    enqueueBufferedText(controller, match);
    buffer = buffer.slice(match.length);
    if (delayInMs !== null) await wait(delayInMs);   // backpressure-friendly pacing INSIDE the loop
  }
}
```

**Flow:** deltas accumulate per (type, part-id) group → each complete detected prefix emits immediately then sleeps `delayInMs` → any non-delta chunk (tool-call, finish, error) forces flush-then-pass-through → `flush()` on stream end emits remaining buffer. Detector contract enforced loudly: custom functions returning empty or non-prefix matches throw TypeError; regexes reset `lastIndex` before exec and must match non-empty prefixes.
**Invariant:** Text/reasoning/part-ids stay in SEPARATE buffer generations (flush on id/type change — test :132); chunk+provider metadata preserved exactly once per emitted group, not duplicated across every word; a trailing metadata-only delta MUST emit even with empty text (#20469 regression); non-delta chunks are never modified.
**Probe:** `packages/core/src/stream/smooth-stream.test.ts`: `keeps text, reasoning, and part ids in separate buffers` (:132), `preserves chunk and provider metadata without duplicating it across emitted chunks` (:160), `flushes a trailing metadata-only delta instead of dropping its providerMetadata (#20469)` (:186), `drops a trailing empty delta without metadata` (:204), `rejects regular expressions that produce empty chunks` (:224).
**Coverage caveat:** none — dedicated vitest suite at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "smoothStream createChunkDetector enqueueBufferedText", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: per-part-id buffer generations, flush-before-non-delta ordering, await-inside-emission-loop pacing, and the metadata-only-tail rule. Adapt the detector vocabulary to your chunk grammar. Omit the Intl.Segmenter branch for ASCII-only products. Porters who merge different part ids into one buffer corrupt multi-part responses; who drop empty-text deltas silently lose Gemini-style thought-signature metadata.
