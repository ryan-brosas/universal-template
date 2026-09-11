<!-- capsule-v2 -->
# UTF-8-safe context chunking — how do you split text into byte-budgeted chunks without corrupting surrogate pairs?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How does a client append long context to a realtime session under a per-message byte cap without splitting inside a character?

## Chunker
**Path/Symbol:** `src/live/protocol.ts:chunkLiveContext` (:212-234) + `utf8ByteLength` (:205-210); cap `CONTEXT_CHUNK_BYTES = 500` (:3).
**Signature:** `chunkLiveContext(text: string): string[]`.
**Data Shape:** In: arbitrary UTF-16 JS string. Out: ordered chunks whose UTF-8 encodings each fit the cap; empty input yields `[""]`.

### Decisive source
```ts
while (index < text.length) {
  const codePoint = text.codePointAt(index);
  if (codePoint === undefined) break;
  const characterLength = codePoint > 0xffff ? 2 : 1;   // UTF-16 units
  const characterBytes = utf8ByteLength(codePoint);      // UTF-8 bytes
  if (chunkBytes + characterBytes > CONTEXT_CHUNK_BYTES) {
    chunks.push(text.slice(chunkStart, index));
    chunkStart = index;
    chunkBytes = 0;
  }
  chunkBytes += characterBytes;
  index += characterLength;                              // advances by CODE POINT
}
chunks.push(text.slice(chunkStart));
```

**Flow:** walk by code point (surrogate pairs advance by 2 via `characterLength`, so a pair is never split) → accumulate true UTF-8 byte cost → flush BEFORE the overflowing char → final tail push.
**Invariant:** Byte budget counts UTF-8 bytes (not UTF-16 length) while slicing stays code-point aligned — counting `.length` would overflow the cap for CJK/emoji; advancing by 1 would tear surrogate pairs into lone surrogates.
**Probe:** `tests/live-protocol.test.ts` (chunk boundary cases incl. multi-byte content reassembling to the original).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "chunkLiveContext CONTEXT_CHUNK_BYTES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-accounting loop (UTF-8 budget, UTF-16 cursor). Adapt the 500-byte cap and chunk-consumption framing (here each chunk becomes one `delegation.context.append`). Omit nothing — this is fully portable; the classic wrong port is `text.slice(i, i+500)` by UTF-16 units.
