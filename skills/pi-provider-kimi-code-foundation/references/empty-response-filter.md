<!-- capsule-v2 -->
# Empty-response stream filter — how do you hide vendor-synthesized "(Empty response…)" text blocks without corrupting session content indices?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** A vendor wraps thinking-only turns into a synthetic text block that leaks internal state to users — how late can you decide a text block is synthetic while still streaming real output?

## Buffered empty-response suppression filter
**Path/Symbol:** `src/stream.ts:98-189` (`EMPTY_RESPONSE_PREFIX`, `filterEmptyResponseStream`); pure async generator, wrapped around the upstream event stream at stream.ts:372.
**Signature:** `(upstream: AsyncIterable<AssistantMessageEvent>) => AsyncIterable<AssistantMessageEvent>`; state = suppressed index set, event buffer, accumulated text, buffering index.
**Data Shape:** passes through all non-text events untouched; decides per text block (identified by shared `contentIndex`) between flush and suppress.

### Decisive source
```ts
if (event.type === "text_delta") {
  bufferedText += event.delta;
  textBuffer.push(event);
  if (bufferedText.startsWith(EMPTY_RESPONSE_PREFIX)) {
    suppressBufferedTextBlock();
    continue;
  }
  if (EMPTY_RESPONSE_PREFIX.startsWith(bufferedText)) {
    continue; // still ambiguous — keep buffering
  }
  yield* flushBufferedTextBlock();
  continue;
}
if (event.type === "text_end") {
  if (event.content.startsWith(EMPTY_RESPONSE_PREFIX)) {
    // Suppress entire text block. Do NOT splice the message content
    // array: it is a shared reference into session state, and mutating
    // it would shift subsequent contentIndex values, corrupting the
    // stream.
    suppressBufferedTextBlock();
  } else {
    yield* flushBufferedTextBlock();
    yield event;
  }
  continue;
}
```
```ts
// Clean suppressed blocks out of the final message.
if (event.type === "done" && suppressedIndices.size > 0) {
  event.message.content = event.message.content.filter(
    (block) =>
      !(
        block.type === "text" &&
        typeof block.text === "string" &&
        block.text.startsWith(EMPTY_RESPONSE_PREFIX)
      ),
  );
}
```

**Flow:** on `text_start` begin buffering that contentIndex → each `text_delta`: if accumulated text already starts with the marker ⇒ suppress immediately; else if accumulated text is still a strict prefix of the marker ⇒ keep buffering (ambiguity window); else ⇒ divergence, flush buffered events and continue streaming live → `text_end` confirms or rejects → events targeting a suppressed index are dropped → at `done`, filter suppressed text blocks out of the final message once → trailing unflushed buffer flushes at stream end.
**Invariant:** The message content array is never spliced mid-stream — it aliases session state and shifting it would corrupt every later contentIndex; cleanup happens only in the done event. Normal text must not be delayed beyond the marker's length (~17 chars), so streaming latency stays bounded.

**Probe:** `tests/payload.test.ts:1052-1118` — line 1053 pins full suppression (`out` types == ["done"], message content keeps only tool_use); 1083 pins byte-identical passthrough of normal blocks; 1095 pins early flush before text_end (events[0] and [1] delivered while upstream still pending).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "filterEmptyResponseStream EMPTY_RESPONSE_PREFIX", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt prefix-buffered suppression with bounded ambiguity windows and done-time content cleanup as the portable shape for hiding vendor-synthesized blocks. Adapt the marker string, block-type vocabulary, and index field name. Omit nothing structural: the no-mid-stream-splice rule is the invariant most ports get wrong. No coverage caveat at this pin.
