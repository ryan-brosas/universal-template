<!-- capsule-v2 -->
# Charset fallback export stream — how do you encode a stream to a legacy charset when most rows fit but some never will, without buffering the whole file?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does a CSV export to windows-1252/GBK/Shift-JIS avoid silently destroying non-representable characters?

## bounded-decision charset Transform
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-export/csv-encoding.ts:createCharsetEncodeStream` (32-123).
**Signature:** `createCharsetEncodeStream(charset: string, onFallback?: () => void, decisionBufferBytes = 64 * 1024): Transform`.
**Data Shape:** three-state machine `deciding | legacy | utf8`; `buffered: string[]` capped at decisionBufferBytes; UTF8_BOM = `Buffer.from('\uFEFF')`.

### Decisive source
```ts
// A charset is lossy for text if encoding then decoding doesn't round-trip.
const isLossy = (text) => iconv.decode(iconv.encode(text, charset), charset) !== text;

if (mode === 'utf8') return cb(null, Buffer.from(text, 'utf8'));
if (mode === 'legacy') return cb(null, getLegacyEncoder().write(text));
if (isLossy(text)) {                       // first non-representable char seen
  mode = 'utf8'; onFallback?.();
  const pending = buffered.join('') + text;
  return cb(null, Buffer.concat([UTF8_BOM, Buffer.from(pending, 'utf8')]));
}
buffered.push(text);
if (bufferedBytes >= decisionBufferBytes) { // enough proof the charset works
  mode = 'legacy';
  return cb(null, getLegacyEncoder().write(buffered.join('')));
}
return cb();                                // keep deciding, emit nothing yet
```

**Flow:** hold up to 64 KB of output while probing each chunk with round-trip encode/decode. A single unrepresentable character (Tibetan in a CJK codepage, emoji in latin-1) flips the WHOLE file to UTF-8 and emits a BOM at byte 0 — Excel then autodetects UTF-8. If the buffer fills clean, commit to the requested legacy charset using one stateful encoder for the rest of the stream.
**Invariant:** reuse ONE `iconv.getEncoder()` for the committed path — a fresh `iconv.encode` per chunk re-emits head-of-stream bytes (UTF-16 BOMs, ISO-2022 escape resets) between every chunk, corrupting output. The BOM can only be prepended because nothing has been emitted during the deciding phase.
**Probe:** no unit test upstream. Source-grounded probe: `csv-encoding.ts:41-51` — lazy singleton encoder with explanatory comment; `:53-56` — isLossy round-trip definition.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "createCharsetEncodeStream iconv BOM transform", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bounded-decision fallback state machine and single stateful encoder; adapt buffer size, charsets offered, and BOM policy to host; omit the data-export job wrapper (see import-streaming capsule's sibling). Coverage caveat: no in-repo tests; source-grounded.
