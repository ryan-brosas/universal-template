<!-- capsule-v2 -->
# Dual SSE fold wrappers — how do you wrap raw SSE bytes into your message stream for two wire dialects with identical failure semantics?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** Where should line-framing, error downcasting, and log-write ordering live so chat-completions and Responses streams behave identically?

## Framing + fold plane
**Path/Symbol:** `crates/goose-providers/src/openai_compatible.rs` : `stream_openai_compat` (236-258) and `stream_responses_compat` (260-282); consumers import both (`crates/goose-providers/src/openai.rs` :20-22; used at :817 and the responses tail).
**Signature:** `pub fn stream_openai_compat(response: Response, log: Option<Box<dyn RequestLogHandle>>) -> Result<MessageStream, ProviderError>` (twin takes the same shape).
**Data Shape:** input = already status-checked `reqwest::Response`; output = boxed stream of `(Message, Option<ProviderUsage>)` items; failure = typed `ProviderError` yielded through the stream.

### Decisive source
```rust
let stream = response.bytes_stream().map_err(std::io::Error::other);
Ok(Box::pin(try_stream! {
    let framed = FramedRead::new(StreamReader::new(stream), LinesCodec::new()).map_err(Error::from);
    let message_stream = response_to_streaming_message(framed);      // ← ONLY difference between the twins:
    pin!(message_stream);                                            //   responses_api_to_streaming_message
    while let Some(message) = message_stream.next().await {
        let (message, usage) = message.map_err(|e|
            e.downcast::<ProviderError>().unwrap_or_else(ProviderError::stream_decode_error))?;
        log.write(&message, usage.as_ref().map(|f| f.usage).as_ref())?;
        yield (message, usage);
    }
}))
```

**Flow:** byte stream → IO-error normalization → `StreamReader` → `FramedRead(LinesCodec)` line framing → dialect-specific SSE fold → per item: preserve already-typed `ProviderError`s, coerce foreign error types into retryable `stream_decode_error`, write the NDJSON log entry BEFORE yielding the item to the consumer.
**Invariant:** The two wrappers differ ONLY in the fold function chosen — framing, downcast policy, and log-before-yield discipline are shared and must stay identical; logging strictly precedes yielding so persisted request logs are prefix-complete relative to what any consumer observed; unknown upstream error types degrade to a typed retryable decode error instead of panicking or being swallowed.
**Probe:** exercised indirectly — the dialect folds themselves carry the deep suites (`cargo test -p goose-provider-types --lib formats::openai` 174 passed / 0 failed recorded pass 3; Responses suite 56 passed pass 4) and the transport deadline matrix lives under `--lib api_client` (10 passed pass 10). Honest caveat: the wrapper layer itself has no dedicated in-file unit test; verified this pass by whole-source read, import-graph consumption (search_code OpenAiCompatibleProvider + openai.rs imports), and compile-green runs within the GREEN suites above.
**Coverage caveat:** none of this pass's cited files are parse-partial; check_index_coverage clean on openai_compatible.rs and openai.rs @ gen 2026-08-24T16:13:03Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "stream_openai_compat stream_responses_compat LinesCodec StreamReader downcast stream_decode_error", limit: 10, fields: ["lines"] });
// executed live this pass: both wrappers located at 236-258 / 260-282 with consumer imports
```

## Verdict
Adopt: one framing wrapper per wire dialect sharing downcast-and-log scaffolding, log-write-before-yield, and typed-error preservation. Adapt the item type and logger interface to your stack. Omit goose's RequestLogHandle SPI if you have no fail-safe NDJSON logging requirement (but keep the ordering property if you keep any log at all).
