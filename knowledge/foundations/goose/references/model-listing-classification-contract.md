<!-- capsule-v2 -->
# Model-listing failure classification — when does /models failure fall back to a static list versus propagate?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** How do you classify ambiguous /models responses so "endpoint not implemented" degrades gracefully while real errors still surface?

## Classification + fallback contract
**Path/Symbol:** `crates/goose-providers/src/openai.rs` : `map_base_path` (521-540), `fetch_models_from_api` (542-570), `parse_model_ids` (589-603), `OpenAiProvider.fetch_supported_models` (732-753); `crates/goose-provider-types/src/errors.rs` : `is_endpoint_not_found` (87-89); anthropic twin `crates/goose-providers/src/anthropic.rs` (215-280).
**Signature:** `async fn fetch_models_from_api(&self) -> Result<Vec<String>, ProviderError>`; `pub fn is_endpoint_not_found(&self) -> bool` (= `matches!(self, EndpointNotFound(_))`).
**Data Shape:** success = sorted id list; classification variants: `EndpointNotFound(body|parse-msg)`, `Authentication(msg)`, `NetworkError(read)`, `RequestFailed(missing-data | untyped)`.

### Decisive source
```rust
if response.status() == StatusCode::NOT_FOUND {                       // checked BEFORE handle_status
    return Err(ProviderError::EndpointNotFound(response.text().await.unwrap_or_default()));
}
let response = handle_status(response).await?;
let json: Value = serde_json::from_slice(&body).map_err(|e|
    ProviderError::EndpointNotFound(format!("Response body is not valid JSON: {}", e)))?; // HTML page ⇒ ENF
if let Some(err_obj) = json.get("error").filter(|error| !error.is_null()) {
    return Err(ProviderError::Authentication(/* error.message */));   // in-band beats status
}
parse_model_ids(&json)   // data[] OR top-level array (together.ai), sorted; else RequestFailed
```
```rust
match self.fetch_models_from_api().await {
    Ok(models) => return Ok(models),
    Err(e) if e.is_endpoint_not_found() => return Ok(names),   // static-list fallback ONLY here
    Err(e) => return Err(e),
}
```

**Flow:** derive the models path from whatever base_path was configured (`chat/completions`→`models`, `responses`→`models`, else fallback constant) → classify in the order above → caller falls back to declared custom models ONLY on `is_endpoint_not_found()`. Anthropic's twin adds a five-way in-band taxonomy by `error.type`: authentication|permission⇒Authentication, rate_limit⇒RateLimitExceeded, billing⇒CreditsExhausted, api|overloaded⇒ServerError, else RequestFailed; its 404 body is parsed for `error.message` before defaulting. `dynamic_models == Some(false)` short-circuits to the static list without any API call.
**Invariant:** Fallback happens exactly when the models ENDPOINT does not exist (HTTP 404 or non-JSON body) — never on auth failures, rate limits, malformed-but-typed errors, or a plain 400 (dedicated test forbids reclassifying 400 as endpoint-not-found); extra sibling fields and literal `"error": null` are tolerated; results are always sorted for determinism.
**Probe:** `cargo test -p goose-providers --lib openai::tests::fetch_supported_models` — falls_back_on_invalid_payload (HTML 200 ⇒ static list), propagates_auth_error (in-band error ⇒ Authentication, no fallback), does_not_reclassify_400_as_endpoint_not_found, accepts_payload_with_extra_fields — 4 passed / 0 failed; `--lib anthropic::tests::fetch_models` 2 passed / 0 failed; `--lib parse_model_ids` 3 passed / 0 failed. All GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "fetch_supported_models fetch_models_from_api endpoint not found fallback static models classification", limit: 10, fields: ["lines"] });
// executed live this pass: openai fetch_models_from_api 542-570 + anthropic twin 215-280 + is_endpoint_not_found 87-89 located
```

## Verdict
Adopt: the ordered classifier (404-before-status → parse-failure-as-endpoint-missing → in-band-error-beats-status → typed array extraction) and the single-variant fallback gate keyed on a dedicated error variant, not string matching. Adapt the in-band taxonomy to your providers' error dialects. Omit goose's canonical-model filtering above this layer.
