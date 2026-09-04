<!-- capsule-v2 -->
# Hashline stream — how do you number lines for a model over unbounded input?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you stream hashline-numbered file content without materializing the whole file?

## Bounded-chunk lazy numbering over byte streams
**Path/Symbol:** `packages/hashline/src/stream.ts:streamHashLines` (95–132), `createChunkEmitter` (32–71), `resolveStreamOptions` (19–25).
**Signature:** `async function* streamHashLines(source: ReadableStream<Uint8Array> | AsyncIterable<Uint8Array>, options?: StreamOptions): AsyncGenerator<string>`.
**Data Shape:** `StreamOptions { startLine?=1, maxChunkLines?=200, maxChunkBytes?=64*1024 }`; each yielded string is `formatNumberedLine` output joined by `\n`, bounded by whichever cap fires first.

### Decisive source
```ts
const sepBytes = outLines.length === 0 ? 0 : 1;
const lineBytes = Buffer.byteLength(formatted, "utf-8");
const wouldOverflow = outLines.length >= maxChunkLines || outBytes + sepBytes + lineBytes > maxChunkBytes;
if (outLines.length > 0 && wouldOverflow) chunks.push(flush());   // flush BEFORE the line
outLines.push(formatted); outBytes += (outLines.length === 1 ? 0 : 1) + lineBytes;
if (outLines.length >= maxChunkLines || outBytes >= maxChunkBytes) chunks.push(flush()); // or AFTER
// decode incrementally; strip one trailing \r per line; final decoder.decode() flushes the tail
if (!sawAnyLine) for (const out of emitter.pushLine("")) yield out; // empty input ⇒ one "1:" line
```

**Flow:** accept `ReadableStream` (wrapped with reader lock release) or any async byte iterable → incremental `TextDecoder({stream:true})` → split on `\n` (CRLF-safe) → emit numbered lines into double-checked chunks (pre-push overflow check, post-push cap check) → final flush yields the remainder.
**Invariant:** a chunk boundary never splits a formatted line; byte budget counts UTF-8 bytes including separators; an empty stream still yields exactly one numbered empty line so consumers always see well-formed `startLine:` output.
**Probe:** direct numbering contract at `packages/hashline/test/format-v2.test.ts:116` (`formatNumberedLines(selected)` === `"1:a\n2:"`). Coverage caveat: `streamHashLines` itself has no dedicated test file in-repo — treat the chunk-boundary math as source-verified but port with your own boundary test (oversized single line, CRLF tail, exact-cap fill).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^streamHashLines$", limit: 5, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.hashline.src.stream.streamHashLines" });
```

## Verdict
Adopt dual-cap chunking with the pre/post-push double check and the empty-input sentinel line; adapt caps and the numbering prefix to your read format; omit the `ReadableStream` branch if your host only exposes async iterables.
