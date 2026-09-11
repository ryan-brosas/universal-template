<!-- capsule-v2 -->
# Anthropic SSE fold — how do you fold Anthropic's event stream into partial messages plus authoritative usage, surviving refusal, truncation, and dropped block-stop events?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** what is the event-to-item fold order, and which tail rules guarantee the consumer still gets tool errors and a final `ProviderUsage` when the stream misbehaves?

## Streaming response machine
**Path/Symbol:** `crates/goose-provider-types/src/formats/anthropic.rs`:`response_to_streaming_message` (853-1185), `merge_delta_usage` (608-636), `get_usage` (638-658).
**Signature:** `pub fn response_to_streaming_message<S>(stream: S) -> impl Stream<Item = anyhow::Result<(Option<Message>, Option<ProviderUsage>)>> where S: Stream<Item = anyhow::Result<String>> + Unpin + Send + 'static`.
**Data Shape:** Input is raw SSE lines (`data: {...}` JSON events, `[DONE]` sentinel). Item = `(Option<Message>, Option<ProviderUsage>)`: message items carry partial text or complete thinking/tool blocks; usage items arrive alone (`None, Some(_)`).

### Decisive source
```rust
// Field-presence-driven merge of cumulative message_delta usage into the
// message_start snapshot (delta input WITHOUT cache keys means fresh-only,
// so start cache tokens carry over).
fn merge_delta_usage(existing: &Usage, delta: &Usage, delta_data: &Value) -> Usage {
    let reports = |key: &str| delta_data.get(key).is_some();
    let output = if reports("output_tokens") { delta.output_tokens } else { existing.output_tokens };
    if !reports("input_tokens") {
        Usage::new(existing.input_tokens, output, None).with_cache_tokens(
            existing.cache_read_input_tokens, existing.cache_write_input_tokens)
    } else if reports("cache_read_input_tokens") || reports("cache_creation_input_tokens") {
        Usage::new(delta.input_tokens, output, None).with_cache_tokens(
            delta.cache_read_input_tokens, delta.cache_write_input_tokens)
    } else {
        Usage::from_cache_exclusive_input(delta.input_tokens, output, None,
            existing.cache_read_input_tokens, existing.cache_write_input_tokens)
    }
}
```
Event grammar (919-1133): `message_start` seeds `message_id` + usage; `content_block_start` registers `tool_use` by id / seeds `ThinkingState` from the block's INITIAL text+signature fields / yields redacted_thinking immediately; deltas — `text_delta` yields a partial Message per chunk, `input_json_delta` appends args, `thinking_delta`/`signature_delta` append to state; `content_block_stop` flushes thinking ONLY if non-empty and flushes the tool call through the parse ladder; `message_delta` merges usage (above), first `stop_reason` wins, `refusal` flushes usage THEN returns `Err(ProviderError::Refusal{details, category})`; unknown event types are logged and skipped.

Tail guarantees (1136-1183):
```rust
// A tool_use block left open at stream end never received its
// content_block_stop, so its args are truncated rather than complete.
if !accumulated_tool_calls.is_empty() {
    let truncated_by_limit = stop_reason.as_deref() == Some("max_tokens");
    let mut ids: Vec<String> = accumulated_tool_calls.keys().cloned().collect();
    ids.sort(); // deterministic error order
    ...
}
if stop_reason.as_deref() == Some("max_tokens") { /* yield marker msg w/ metadata.output_token_limit_reached */ }
if let Some(mut usage) = final_usage { /* finish_reasons + response_id attached */ yield (None, Some(usage)); }
```

**Flow:** line filter (`data:` prefix, optional space; `[DONE]` breaks; unparseable JSON → debug-log + continue) → per-event state updates → post-loop tail emits leftover truncated tool calls as `ToolRequest(id, Err(INVALID_PARAMS))`, then the max-tokens marker message, then exactly one usage item.
**Invariant:** malformed accumulated arguments NEVER crash or vanish — they surface as an Err-carrying ToolRequest whose guidance distinguishes max-tokens truncation from generic incompleteness; refusal turns are still billed (usage flushed before the error); every successful stream ends with a usage item carrying `finish_reasons`/`response_id`.
**Probe:** `cargo test -p goose-provider-types --lib anthropic` — pins `test_streaming_truncated_tool_args_no_content_block_stop`, `test_streaming_truncated_tool_args_in_content_block_stop`, `test_streaming_refusal` (+ unrecognized stop_details forwarding), `test_streaming_delta_usage_is_cumulative_and_wins`, `test_merge_delta_usage_raw_input_inherits_start_cache`, `test_streaming_marks_max_tokens`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "response_to_streaming_message merge_delta_usage content_block_stop", limit: 10, fields: ["lines"] });
```

## Verdict
Adopt the fold grammar, the field-presence usage merge, and the three tail rules — they make a fragile vendor stream consumable without inventing a second error channel. Adapt event names/shapes to your provider dialect and the refusal payload extraction (`explanation` → stringified details → fallback sentence) to your error taxonomy. Omit goose-specific cost plumbing (`provider_usage_with_cost` borrowing openai's `get_cost`) unless you share the same usage model.
