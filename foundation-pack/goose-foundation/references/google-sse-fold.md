<!-- capsule-v2 -->
# Google SSE fold — how do Gemini stream chunks become same-id messages with reconciled thinking-token usage?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how should a Gemini `streamGenerateContent` SSE be folded so partial JSON survives chunk splits, all deltas share one message id, and reasoning tokens land inside output tokens?

## response_to_streaming_message line machine
**Path/Symbol:** `crates/goose-provider-types/src/formats/google.rs::response_to_streaming_message` (:446-580).
**Signature:** `fn response_to_streaming_message<S: Stream<Item = anyhow::Result<String>> + Unpin + Send>(stream: S) -> impl Stream<Item = anyhow::Result<(Option<Message>, Option<ProviderUsage>)>>`.
**Data Shape:** per-chunk Google JSON `{candidates:[{content:{parts},finishReason}],usageMetadata,modelVersion,responseId}` or `{error:{code,message,status}}`; state = final_usage, last_signature (shared with process_response_part_impl), stream_id UUID, incomplete_data buffer, last_finish_reason/response_id.

### Decisive source
```rust
let data_part = if line.starts_with("data: ") { line.strip_prefix("data: ").unwrap() }
else if line.starts_with("event:") || line.starts_with("id:") || line.starts_with("retry:") { continue; }
else if incomplete_data.is_some() { &line }   // continuation of a split JSON payload
else { continue };
// ...
Err(e) => {
    if e.is_eof() { continue; }               // still incomplete → keep buffering
    tracing::warn!("Failed to parse streaming chunk: {}", e);
    incomplete_data = None;                    // hard error → drop buffer, skip chunk
    continue;
}
if let Some(error) = chunk.get("error") {
    Err::<(), ProviderError>(ProviderError::RequestFailed(
        format!("Google API error ({status}): {message}")))?;
}
```

**Flow:** blank lines skipped → `event:`/`id:`/`retry:` fields skipped → non-prefixed lines consumed ONLY while a partial payload is open → EOF-shaped parse errors extend the buffer, real errors drop it → `[DONE]` breaks → error frames fail loudly with status+message → every serialized part becomes a single-block Message sharing ONE generated `stream_id` (collect_stream later coalesces them) → after loop end, one usage-only yield carries finish_reasons + response_id.
**Invariant:** content parts never yield usage and usage never yields content (the tuple contract stays clean); a mid-stream error aborts immediately rather than emitting partial text first.
**Probe:** `crates/goose-provider-types/src/formats/google.rs::test_streaming_text_response` (:1428-1469 — identical ids across deltas); `test_streaming_with_sse_event_lines` (:1621-1648); `test_streaming_handles_done_signal` (:1651-1681); `test_streaming_error_response` (:1599-1618).

## Usage reconciliation
**Path/Symbol:** `formats/google.rs::get_usage` (:399-444).
**Signature:** `fn get_usage(data: &Value) -> Result<Usage>`.
**Data Shape:** promptTokenCount / candidatesTokenCount / thoughtsTokenCount / totalTokenCount / cachedContentTokenCount.

### Decisive source
```rust
// `candidatesTokenCount` is the visible output; thinking models
// (Gemini 2.5/3) report reasoning tokens separately in
// `thoughtsTokenCount`, and per the API spec `totalTokenCount` =
// prompt + thoughts + candidates. Fold thoughts into `output_tokens` so
// the record reconciles (input + output == total) and cost, which
// Google bills at the output rate, is correct -- matching the OpenAI
// (completion_tokens includes reasoning) and Anthropic (output_tokens
// includes thinking) adapters.
let output_tokens = match (candidates_tokens, thoughts_tokens) {
    (None, None) => None,
    (candidates, thoughts) => Some((candidates.unwrap_or(0) + thoughts.unwrap_or(0)) as i32),
};
```

**Flow:** usage read from EVERY chunk; last chunk with any token counts wins (`final_usage` replaced) → missing usageMetadata degrades to an all-None Usage with a debug log (never an error) → promptTokenCount already contains cachedContentTokenCount, so cache tokens are reported without double-counting input.
**Invariant:** `input + output == total` must hold post-fold; absent usage is a silent None, not a failure.
**Probe:** `test_get_usage_includes_thinking_tokens` (:870-894); `test_get_usage` (:835-849); streaming metadata attach asserted by `test_streaming_response_metadata` (:1472-1493).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "google format_messages functionResponse inline_data nested media tool_names", limit: 8 });
```
Companion retrieval for this seam executed live at pin via the signature-plane query ("thought signature loop boundary synthetic…"), which surfaced `test_streaming_with_thought_signature` :1523-1596 — proving signature-bearing text parts stay TEXT unless `thought:true`, across three interleavings.

## Verdict
Adopt the eof-buffered line machine, single-stream-id delta emission, and the thoughts→output token fold (it keeps cross-provider cost math comparable); adapt field names to your Gemini API revision; omit modelVersion tracking if you do not need per-response model provenance. Coverage: google.rs no_recorded_issue + metadata_match; direct tests green (35 passed / 0 failed).
