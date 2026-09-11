<!-- capsule-v2 -->
# Provider trait surface and collect_stream fold kernel — what is the minimal provider-trait design, and how must streamed chunks fold into one message without corrupting block boundaries?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how do you shape a provider trait so only streaming is mandatory, and how do you fold a stream of partial messages into a single Message + usage while preserving text-audience and signed-thinking block boundaries?

## Provider trait default surface + MessageStream fold
**Path/Symbol:** `crates/goose-provider-types/src/base.rs:Provider` (trait, 478-725), `collect_stream` (381-471), `MessageStream` type alias (341-343), `stream_from_single_message` (473-476).
**Signature:** `type MessageStream = Pin<Box<dyn Stream<Item = Result<(Option<Message>, Option<ProviderUsage>), ProviderError>> + Send>>`; `async fn stream(&self, model_config, system, messages, tools) -> Result<MessageStream>` is the ONLY required method; `async fn collect_stream(stream: MessageStream) -> Result<(Message, ProviderUsage), ProviderError>`.
**Data Shape:** stream items carry an optional partial Message plus an optional ProviderUsage; text streams partially, tool calls arrive complete. Default trait methods supply everything else: `complete()` = stream+collect_stream; `get_context_limit`; `retry_config()`; `fetch_supported_models`/`fetch_recommended_models(toolshim)` (canonical-registry filter, release-date sort, empty-filter falls back to ALL inventory models so unknown future models survive); `manages_own_context()`→`supports_builtin_tools()`; `configure_oauth`/`refresh_credentials` default-erroring; `thinking_effort_support()`, `subscribe_thinking_effort_support() -> Option<watch::Receiver<_>>`, `set_thinking_effort(..) -> Ok(true)=applied | Ok(false)=legacy path`.

### Decisive source
```rust
// base.rs — folding rules inside collect_stream; multi-block chunks are structured units,
// not deltas: their blocks NEVER merge into prior state (mirrors Conversation::push gate).
let is_single_block_delta = msg.content.len() == 1;
for new_content in msg.content {
    match (&mut prev.content.last_mut(), &new_content) {
        // Coalesce consecutive text blocks only when audience annotations are equal
        (Some(MessageContentBlock::Text(last_text)), MessageContentBlock::Text(new_text))
            if last_text.annotations.as_ref().and_then(|a| a.audience.as_ref())
                == new_text.annotations.as_ref().and_then(|a| a.audience.as_ref()) =>
        { last_text.text.push_str(&new_text.text); }
        // Thinking coalesces only for single-block deltas while the previous block is
        // unsigned or the incoming delta shares its signature
        (Some(MessageContentBlock::Thinking(last_thinking)), MessageContentBlock::Thinking(new_thinking))
            if is_single_block_delta
                && (last_thinking.signature.is_empty()
                    || new_thinking.signature == last_thinking.signature) =>
        {
            last_thinking.thinking.push_str(&new_thinking.thinking);
            if !new_thinking.signature.is_empty() { last_thinking.signature = new_thinking.signature.clone(); }
        }
        _ => { prev.content.push(new_content); }
    }
}
...
match (final_message, final_usage) {
    (Some(msg), usage) => Ok((msg, usage.unwrap_or_else(|| ProviderUsage::new("unknown".into(), Usage::default())))),
    (None, Some(usage)) => Ok((Message::new(Role::Assistant, now, vec![]), usage)),
    (None, None) => Err(ProviderError::ExecutionError("Stream yielded no message".into())),
}
```

**Flow:** provider yields chunks → collect_stream folds: equal-audience Text appends into the previous Text block; single-block unsigned/equal-signed Thinking appends (adopting any closing signature); anything else starts a NEW block; last Some(usage) wins → final fallbacks: no message but usage ⇒ empty assistant message; neither ⇒ ExecutionError.
**Invariant:** a signed thinking block never absorbs a differently-signed delta; an unsigned body adopts the closing signature when it arrives; the first block of a MULTI-block chunk never merges backwards; missing usage becomes `model="unknown"` rather than an error; an entirely empty stream is an error, not silence.
**Probe:** `cargo test -p goose-provider-types --lib base` — part of the observed GREEN run `cargo test -p goose-provider-types --lib` (551 passed / 0 failed): `test_collect_stream_coalescing` (4 cases), `test_collect_stream_defaults_usage`, `test_collect_stream_usage_only_yields_empty_message`, `test_collect_stream_no_message_no_usage_errors`, `test_collect_stream_preserves_text_audience_boundaries`, `test_collect_stream_coalesces_thinking_deltas`, `test_collect_stream_never_merges_distinctly_signed_thinking_blocks`, `test_collect_stream_unsigned_body_adopts_closing_signature`, `test_collect_stream_unsigned_thinking_after_signed_starts_a_new_block`, `test_collect_stream_multi_block_chunk_does_not_merge_into_prior_thinking` (regression for a maintainer-caught signing bug), `recommended_models_preserve_unknown_future_models`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "collect_stream MessageStream Provider complete stream", limit: 8 });
// located: base.rs:collect_stream 381-471, test_collect_stream_coalescing 825-830, anthropic.rs:collect_stream 2234-2265
```

## Verdict
Adopt the "only stream() is required" trait with defaulted capability methods, the MessageStream item shape, and the three-fold rule (equal-audience text merge; signature-gated single-block thinking merge; append otherwise) with its usage/empty-stream fallbacks. Adapt fetch_recommended_models' registry filtering to your own catalog; keep the empty-filter→all-models fallback. Omit the CanonicalModelRegistry plumbing and ACP/session hooks (`resume`, `update_mode`, `apply_model_selection`) unless porting the full agent. Coverage: base.rs `no_recorded_issue` + `metadata_match`; direct tests GREEN.
