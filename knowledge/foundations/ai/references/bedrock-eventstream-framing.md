<!-- capsule-v2 -->
# Bedrock event-stream framing — how do length-prefixed binary frames become typed events without silent loss?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** ConverseStream rides smithy's binary event format — what does the decoder guarantee about partial frames, decode failures, and exception frames?

## Length-prefix accumulator with fail-loud boundaries
**Path/Symbol:** `packages/amazon-bedrock/src/amazon-bedrock-event-stream-decoder.ts:createAmazonBedrockEventStreamDecoder` (:16–70).
**Signature:** `(body: ReadableStream<Uint8Array>, processEvent(event: DecodedEvent, controller)) => ReadableStream<T>` where `DecodedEvent = {messageType, eventType?, exceptionType?, data}`.
**Data Shape:** Frames carry smithy headers `:message-type` (`event`|`exception`), `:event-type`/`:exception-type`, UTF-8 body.

### Decisive source
```ts
while (buffer.length >= 4) {
  const totalLength = new DataView(buffer.buffer, buffer.byteOffset,
    buffer.byteLength).getUint32(0, false);        // big-endian u32 prefix
  if (buffer.length < totalLength) break;          // wait for full frame
  const decoded = codec.decode(buffer.subarray(0, totalLength));
  buffer = buffer.slice(totalLength);
  await processEvent({ messageType, eventType, exceptionType,
    data: textDecoder.decode(decoded.body) }, controller);
}
flush() { if (buffer.length > 0)
  throw new Error(`Incomplete Amazon Bedrock event-stream frame: ${buffer.length} buffered bytes remain at end of stream.`); }
```
NOTE: an earlier revision wrapped decode+processEvent in try/catch-break — REMOVED by #18996 so decoding failures surface instead of silently truncating streams mid-flight.

**Flow:** append chunks to one Uint8Array → loop while a 4-byte length prefix is readable → break until the whole frame arrived → decode → dispatch by message-type (exception frames route through processEvent too, carrying `exceptionType`) → flush throws if ANY bytes remain (truncated tail = loud error, never a fake-clean end).
**Invariant:** Frame boundaries are authoritative; neither decode failures nor truncated tails may be swallowed. Companion handler work (#19039) surfaces modeled ConverseStream exception frames as proper error parts upstream of this decoder.
**Probe:** deterministic probes: `grep -c "getUint32(0, false)" packages/amazon-bedrock/src/amazon-bedrock-event-stream-decoder.ts` → `1`; `grep -c "Incomplete Amazon Bedrock event-stream frame" …ts` → `1`. Direct tests: `amazon-bedrock-event-stream-decoder.test.ts` (new, 108 lines) + `…event-stream-response-handler.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createAmazonBedrockEventStreamDecoder", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the accumulator + big-endian prefix + fail-loud flush; adapt the codec dependency (@smithy/eventstream-codec) or reimplement the vnd.amazon.eventstream framing; NEVER reintroduce catch-and-stop around per-frame processing — that was the bug.
