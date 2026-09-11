<!-- capsule-v2 -->
# extractJsonMiddleware — how do you strip a markdown fence from a STREAM when the closing ``` may arrive split across deltas?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you remove ```` ```json\n ```` prefixes and ```` \n``` ```` suffixes from streamed text without ever emitting a partial fence or trimming already-streamed bytes?

## extract-json-middleware.ts
**Path/Symbol:** `packages/ai/src/middleware/extract-json-middleware.ts:extractJsonMiddleware` (:33-207 whole); helpers `defaultTransform` (:11-16), `stripMarkdownCodeFenceSuffix` (:18-20).
**Signature:** `extractJsonMiddleware(options?: { transform?: (text: string) => string }): LanguageModelMiddleware` — implements `wrapGenerate` + `wrapStream`.
**Data Shape:** per-stream `textBlocks: Record<string, { startEvent; phase: 'prefix'|'streaming'|'buffering'; buffer: string; prefixStripped: boolean }>` built on `createIdMap()` (prototype-less — see invariant 4); constant `SUFFIX_BUFFER_SIZE = 12`.

### Decisive source
```ts
const SUFFIX_BUFFER_SIZE = 12;
// text-delta, phase 'streaming':
if (block.phase === 'streaming' && block.buffer.length > SUFFIX_BUFFER_SIZE) {
  const toStream = block.buffer.slice(0, -SUFFIX_BUFFER_SIZE);
  block.buffer = block.buffer.slice(-SUFFIX_BUFFER_SIZE);   // last 12 chars are ALWAYS held back
  controller.enqueue({ type: 'text-delta', id: chunk.id, delta: toStream });
}
// text-end:
} else {
  // Only strip the suffix. Since earlier text may already have
  // streamed, trimming the remaining suffix would remove valid
  // leading whitespace at the stream boundary.
  remaining = stripMarkdownCodeFenceSuffix(remaining);
}
```

**Flow:** GENERATE path transforms every `type==='text'` content part through `transform`, passes non-text parts untouched (:47-64). STREAM path runs a TransformStream state machine per text id: `prefix` phase buffers until it can PROVE there is no fence (first non-backtick char → flush startEvent + stream) or until a full fence+newline matches `/^```(?:json)?\s*\n/` (strip prefix, set `prefixStripped`, then stream); a custom `transform` forces `buffering` of the ENTIRE text because arbitrary transforms are not decomposable (:91). During streaming, all bytes flow through a rolling buffer that emits only `buffer[0:-12]`, holding back 12 chars. At `text-end`: still-buffered blocks get their startEvent emitted first (:167-169), then exactly one of {full transform (buffering or never-streamed prefix), suffix-only strip (`stripMarkdownCodeFenceSuffix`) once streaming began}; leftover non-empty remainder is emitted before the original `text-end` chunk and the block is deleted (:164-197).
**Invariant:** (1) The 12-char holdback exists so a closing fence SPLIT ACROSS DELTAS can never be partially emitted (test :386 'should handle fence split across multiple deltas'; :677 'large content exceeding suffix buffer'). A porter who streams bytes immediately WILL ship half a fence to the consumer. (2) Once any byte has streamed, end-of-text may ONLY strip the suffix — running full `transform` again would delete valid leading whitespace at the boundary (source comment :181-183 IS the invariant; test :353 'preserve leading space in final streamed suffix'). (3) Prefix detection must not block on `'`'` forever: ≥3 chars not starting with ```` ``` ```` flips to streaming (:139-145; test :426 'starts with backtick but is not a fence', :878 'quickly switching to streaming'); a lone newline inside a backtick buffer WITHOUT the fence pattern also releases (:132-136). (4) The chunk-id map MUST be prototype-less (`createIdMap()` → `Object.create(null)`): a hostile `id: "__proto__"` delta would otherwise resolve to `Object.prototype` and pollute it (test :199 'should not read Object.prototype for missing text part ids' asserts `Object.hasOwn(Object.prototype,'buffer')===false`). (5) Deltas for ids with no tracked `text-start` pass through unchanged (:100-103; test :561). (6) Empty transform results emit nothing but still emit `text-end` (:187-194; test :843).
**Probe:** `bash -c "grep -c SUFFIX_BUFFER_SIZE $REFERENCE_ROOT/ai/packages/ai/src/middleware/extract-json-middleware.ts && grep -c 'Object.create(null)' $REFERENCE_ROOT/ai/packages/ai/src/util/create-id-map.ts"` → `4` and `1`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "extractJsonMiddleware wrapStream defaultTransform stripMarkdownCodeFenceSuffix", limit: 5 });
// → ai.packages.ai.src.middleware.extract-json-middleware.extractJsonMiddleware Function packages/ai/src/middleware/extract-json-middleware.ts 33-207
```

## Verdict
Adopt the three-phase state machine, the 12-char suffix holdback, and the prototype-less id map as an inseparable unit — they encode one behavior: fence stripping that is invisible to the consumer. Adapt buffer size only if your fence grammar can exceed 12 chars across a delta boundary. Omit custom-transform buffering if you allow only the default fence stripper.
