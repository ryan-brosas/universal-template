<!-- capsule-v2 -->
# OpenAI-compatible thin-client kernel — when is a new provider configuration instead of code, and how do path prefixes compose?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** What is the minimal state a generic chat-completions client needs, and how do gateways like Azure express their path quirks without forking the client?

## Thin-client kernel
**Path/Symbol:** `crates/goose-providers/src/openai_compatible.rs` : `OpenAiCompatibleProvider` (31-53), `build_request_for_model` (56-81), `stream_payload` (104-147), `impl Provider` (169-225); flagship consumer `crates/goose-providers/src/azure_foundry.rs` : `AzureFoundryProvider.create` (162-254).
**Signature:** `OpenAiCompatibleProvider::new(name: String, api_client: ApiClient, completions_prefix: String)` + `with_supports_streaming(bool)`; `async fn stream_payload(&self, model_config, payload) -> Result<MessageStream, ProviderError>`.
**Data Shape:** exactly four fields: display `name`; `api_client` targeted at the base URL host; `completions_prefix` prepended to `chat/completions` (e.g. `"deployments/{name}/"` for Azure-style gates); `supports_streaming` flag. Request = POST `{prefix}chat/completions`.

### Decisive source
```rust
let response = self.with_retry(|| async {
    handle_status(
        self.api_client.request(&path)            // path = format!("{}chat/completions", prefix)
            .model_headers(model_config)?
            .streaming(self.supports_streaming)
            .response_post(&payload).await?,
    ).await
}).await.inspect_err(|e| { let _ = log.error(e); })?;
```
```rust
// azure_foundry.create — ONE endpoint fans out into three engines:
let chat_prefix = if native_inference { "openai/v1/" } else { "v1/" };
let chat = OpenAiCompatibleProvider::new(NAME, chat_client, chat_prefix.to_string());
// …responses via OpenAiProviderBuilder.base_path("openai/v1/responses").skip_canonical_filtering(true)
// …anthropic via AnthropicProviderBuilder on {hub}/anthropic + anthropic-version header
```

**Flow:** payload built by the shared format layer (`create_request_for_model_with_options`, ImageFormat::OpenAi) with a wire_model/capability_model SPLIT and hardcoded `preserve_thinking_context: true`; send under retry + status funnel; fold via `stream_openai_compat` or the non-streaming branch. Trait surface: only `stream()` plus passthroughs — `refresh_credentials` maps ApiClient errors to `Authentication`; `fetch_supported_models` GETs `models`, maps an in-band error object to `Authentication` regardless of HTTP status, requires `data[].id`, returns SORTED names.
**Invariant:** The generic client owns NO provider-specific payload logic beyond its four config fields and the two format-option flags; bespoke behavior lives in WRAPPERS holding an inner instance (xai/avian/gondola/huggingface/azure providers all keep one), or in per-engine builders — never in forks of this file. Prefix composition means the client must treat `completions_prefix` as an opaque path fragment ending before the literal `chat/completions`.
**Probe:** `cargo test -p goose-providers --lib openai_compatible` — 11 passed / 0 failed at pin (8-case status→telemetry table incl. 402±payload→CreditsExhausted, 400 context-length→ContextLengthExceeded; non-streaming trio). Consumer wiring pinned by source read of azure_foundry.create (:189–243).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "OpenAiCompatibleProvider completions_prefix supports_streaming stream_payload model_headers", limit: 10, fields: ["lines"] });
// executed live this pass: build_request/build_request_for_model/stream_payload/stream_openai_compat located with ranges
```

## Verdict
Adopt: four-field generic client + prefix-composed endpoint + shared format-layer payloads + wrapper-not-fork extension rule. Adapt the auth/header injection point (goose bakes it into ApiClient defaults) and the model-headers hook. Omit Azure Foundry's multi-engine fan-out specifics unless you serve that gateway.
