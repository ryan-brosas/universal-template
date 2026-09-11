<!-- capsule-v2 -->
# Non-streaming mode tri-effect — how do you support providers that cannot stream without forking anything downstream?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** Which exact behaviors must flip together when streaming is disabled, and how does the rest of the stack stay unaware?

## One flag, three coupled effects
**Path/Symbol:** `crates/goose-providers/src/openai_compatible.rs` : `with_supports_streaming` (50-53), flag use sites (99, 117, 127-146) + tests (361-453); twin tail in `crates/goose-providers/src/openai.rs` (816-839).
**Signature:** `supports_streaming: bool` flows into `build_request_for_model(…, for_streaming)`, `.streaming(flag)`, and the response-fold branch.
**Data Shape:** streaming=false ⇒ payload WITHOUT `stream`/`stream_options` keys; request carries reqwest TOTAL timeout (client deadline kernel); response consumed as bounded JSON.

### Decisive source
```rust
if self.supports_streaming {
    stream_openai_compat(response, log)
} else {
    let json = read_json_response(response).await?;          // MAX_PROVIDER_JSON_RESPONSE_BYTES bound
    let message = response_to_message(&json).map_err(|e| ProviderError::RequestFailed(format!("Failed to parse message: {}", e)))?;
    let usage_json = json.get("usage").unwrap_or(&Value::Null);
    let mut usage = ProviderUsage::new(model_config.model_name.clone(), get_usage(usage_json));
    record_response_metadata(&mut usage, &json);
    if let Some(cost) = get_cost(usage_json) { usage = usage.with_cost(cost, CostSource::ProviderReported); }
    log.write(&serde_json::to_value(&message).unwrap_or_default(), Some(&usage.usage))?;
    Ok(stream_from_single_message(message, usage))
}
```
```rust
assert_eq!(payload.get("stream"), None);
assert_eq!(payload.get("stream_options"), None);
```

**Flow:** flag set once at construction → (1) request payload generated with `for_streaming=false` so no streaming keys appear; (2) HTTP request marked `.streaming(false)` which attaches the total-deadline timeout instead of the streaming send-phase split; (3) response body read through the byte-capped JSON reader, mapped to a Message + ProviderUsage (+provider-reported cost), logged, then wrapped by `stream_from_single_message`.
**Invariant:** All three effects are driven by the SINGLE constructor flag — no call site may re-derive them independently; downstream consumers always receive a `MessageStream` either way, so agent/session layers never learn the mode. Body reads are bounded even in the "safe" non-streaming path (oversized ⇒ error containing "response body exceeds").
**Probe:** `cargo test -p goose-providers --lib openai_compatible` — `build_request_respects_non_streaming_mode` (both keys absent), `nonstreaming_completion_accepts_legitimate_response` (wiremock 200 choices ⇒ stream ok), `nonstreaming_completion_rejects_oversized_response_body` (>16MiB body rejected). 11 passed / 0 failed at pin.
**Engine contrast (port as capability constraints):** ollama (`ollama.rs` :350–355) and anthropic (`anthropic.rs` :464–469) HARD-ERROR at construction on `supports_streaming:false` ("All Ollama/Claude models support streaming") instead of implementing the fallback.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "supports_streaming non streaming read_json_response stream_from_single_message usage cost", limit: 10, fields: ["lines"] });
// executed live this pass: stream_payload 104-147 + openai.rs twin tail 816-839 + both non-streaming wiremock tests located
```

## Verdict
Adopt: single-flag tri-effect coupling and the MessageStream-preserving fold so callers stay mode-blind; keep the byte cap on buffered bodies. Adapt the usage/cost extraction to your token model. Choose per engine whether non-streaming is a supported mode (openai engine) or a construction-time capability error (ollama/anthropic engines) — do not mix silently.
