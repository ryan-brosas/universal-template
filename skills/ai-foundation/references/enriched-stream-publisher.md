<!-- capsule-v2 -->
# Enriched stream + partial-output publisher — how do you attach streaming parse results to a pass-through chunk stream without dropping or duplicating text?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What is the `EnrichedStreamPart` envelope, and which rules govern the first-text-chunk lock and publish-once cursor in `createOutputTransformStream`?

## The envelope
**Path/Symbol:** `packages/ai/src/generate-text/stream-text.ts:EnrichedStreamPart` (839–842) + `createOutputTransformStream` (850–954).
**Signature:** `type EnrichedStreamPart<TOOLS, PARTIAL_OUTPUT> = { part: TextStreamPart<TOOLS>; partialOutput: PARTIAL_OUTPUT | undefined }`.
**Data Shape:** every downstream consumer (eventProcessor, `.stream`, `partialOutputStream`, `elementStream`) reads this PAIR; `partialOutput` is non-null only on the single `text-delta` that carried a newly parsed value.

### Decisive source
```ts
// we have to pick a text chunk which contains the json text
// since we are streaming, we have to pick the first text chunk
if (firstTextChunkId == null) {
  firstTextChunkId = chunk.id;
} else if (chunk.id !== firstTextChunkId) {
  controller.enqueue({ part: chunk, partialOutput: undefined });
  return;
}
...
// only publish new value if it has changed:
const currentValue =
  typeof result.partial === 'string'
    ? result.partial
    : JSON.stringify(result.partial);
if (currentValue !== lastPublishedValue) {
  publishTextChunk({ controller, partialOutput: result.partial });
  lastPublishedValue = currentValue;
}
```
(stream-text.ts:905–912, 941–950, verbatim)

**Flow:** non-text chunks pass through with `partialOutput: undefined` → the FIRST `text-*` chunk id is locked as the parse carrier → deltas on OTHER ids pass through unenriched (multi-paragraph responses never double-parse) → carrier deltas accumulate into both full `text` and unsent `textChunk` buffers → `output.parsePartialOutput({text})` runs per delta → a NEW parsed value flushes the pending buffer as one re-emitted `text-delta` carrying `partialOutput` → `finish-step`/`text-end` flush any unparsed tail first so no text is lost.
**Invariant:** (1) The id LOCK means enrichment follows exactly one text part — a porter who parses across all text parts emits interleaved garbage for parallel text blocks. (2) Dedupe by stringified comparison: unchanged parses are swallowed, so consumers can treat each non-null `partialOutput` as a state CHANGE. (3) Buffer-before-publish guarantees the re-emitted delta contains ALL accumulated-but-unforwarded text — naive immediate forwarding duplicates characters. (4) `null` is a legal JSON value and must still publish; `undefined` from the parser means "not parsable yet", not "empty".
**Probe:** `stream-text.test.ts:20030/20081/20122` (`partialOutputStream` sequences), element-stream publication at :20778/:20862.

## Downstream fan-out via tee
**Path/Symbol:** `DefaultStreamTextResult.teeStream` (2637–2641) + accessors (2643–2754).
**Signature:** `private teeStream() { const [s1, s2] = this.baseStream.tee(); this.baseStream = s2; return s1; }`.
**Flow:** each accessor (`textStream`, `stream`, `partialOutputStream`, `elementStream`) tees off the CURRENT base and REPLACES it, so N subscribers each see the full enriched stream exactly once.
**Invariant:** tee-and-replace ordering makes subscription order irrelevant but means every accessor must be consumed (or dropped) before backpressure stalls the shared pipeline. `elementStream` throws `UnsupportedFunctionalityError` unless the output spec implements `createElementStreamTransform` (:2728–2740) — guard before offering element UIs.
**Probe:** `stream-text.test.ts:20778` elementStream emission vs `output.ts` factories returning `undefined` transforms.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "EnrichedStreamPart createOutputTransformStream partialOutput", limit: 10 });
```
Pattern echo: the harness package re-declares its own `EnrichedStreamPart` (`packages/harness/src/agent/internal/harness-stream-text-result.ts:50`) — the envelope shape, not the module, is the portable unit.

## Verdict
Adopt the `{part, partialOutput}` pair, the single-carrier id lock, stringify-dedupe publishing, buffer-flush on boundaries, and tee-and-replace fan-out. Adapt the parser hook signature to your host's partial-parse contract. Omit providerMetadata passthrough subtleties unless porting signed reasoning. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2; decisive ranges read at HEAD this session.
