<!-- capsule-v2 -->
# Provider error taxonomy with credential/URL redaction — typed error enum, reqwest→ProviderError mapping, and secret-free diagnostics

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how to model a provider-call failure taxonomy as a typed error enum with a telemetry type tag, and map raw `reqwest`/`anyhow` errors into it while stripping credentials from URLs and query strings so diagnostics never leak secrets?

## ProviderError and reqwest mapping
**Path/Symbol:** `crates/goose-provider-types/src/errors.rs:ProviderError` (enum), `ProviderError::telemetry_type` (27-46), `ProviderError::from_stream_error` (58-63), `is_network_error` (66-69), `sanitized_reqwest_url` (71-77), `reqwest_error_category` (79-92), `provider_error_from_reqwest` (94-136), `From<anyhow::Error>` (138-167), `From<reqwest::Error>` (169-171), `GoogleErrorCode` (176-211).
**Signature:** `enum ProviderError { NotConfigured, Authentication(String), ContextLengthExceeded(String), RateLimitExceeded{details,retry_delay:Option<Duration>}, ServerError(String), NetworkError(String), RequestFailed(String), InvalidValue(String), ExecutionError(String), UsageError(String), NotImplemented(String), EndpointNotFound(String), CreditsExhausted{details,top_up_url}, Refusal{details,category} }`; `fn telemetry_type(&self) -> &'static str`; `fn from_stream_error(error: anyhow::Error) -> Self`.
**Data Shape:** each variant carries a human message; `RateLimitExceeded`/`CreditsExhausted` carry structured detail fields. `telemetry_type` maps each variant to a stable short string (`not_configured`, `auth`, `context_length`, `rate_limit`, `server`, `network`, `request`, `invalid_value`, `execution`, `usage`, `not_implemented`, `endpoint_not_found`, `credits_exhausted`, `refusal`).

### Decisive source
```rust
// errors.rs — network classification and secret-free URL sanitization
fn is_network_error(err: &reqwest::Error) -> bool {
    err.is_connect() || err.is_timeout() || (err.status().is_none() && err.is_request())
}

fn sanitized_reqwest_url(error: &reqwest::Error) -> Option<String> {
    let mut url = error.url()?.clone();
    let _ = url.set_password(None);
    let _ = url.set_username("");
    url.set_query(None);
    url.set_fragment(None);
    Some(url.to_string())
}

fn provider_error_from_reqwest(error: &reqwest::Error) -> ProviderError {
    if is_network_error(error) {
        let msg = if error.is_timeout() {
            "Request timed out — check your network connection and try again.".to_string()
        } else if error.is_connect() {
            // host/port extracted from the URL, credential-free
            ...
        } else {
            "Network error — check your network connection and try again.".to_string()
        };
        return ProviderError::NetworkError(msg);
    }
    let mut details = Vec::new();
    if let Some(status) = error.status() { details.push(format!("status: {}", status)); }
    if let Some(url) = sanitized_reqwest_url(error) { details.push(format!("url: {url}")); }
    let category = reqwest_error_category(error);
    let msg = if details.is_empty() { category.to_string() }
        else { format!("{category} ({})", details.join(", ")) };
    ProviderError::RequestFailed(msg)
}

// From<anyhow::Error>: unwrap a nested ProviderError, else a reqwest error, else
// a tokio Elapsed -> NetworkError, else ExecutionError(error.to_string()).
impl From<anyhow::Error> for ProviderError {
    fn from(error: anyhow::Error) -> Self {
        if let Some(provider_error) = error.chain().find_map(|c| c.downcast_ref::<ProviderError>()) {
            return provider_error.clone();
        }
        if let Some(reqwest_err) = error.chain().find_map(|c| c.downcast_ref::<reqwest::Error>()) {
            return provider_error_from_reqwest(reqwest_err);
        }
        if error.chain().any(|c| c.downcast_ref::<tokio::time::error::Elapsed>().is_some()) {
            return ProviderError::NetworkError("Request timed out — ...".to_string());
        }
        ProviderError::ExecutionError(error.to_string())
    }
}
```

**Flow:** `provider_error_from_reqwest` first classifies network errors (connect/timeout/request-without-status) into a friendly `NetworkError` message; otherwise it builds a `RequestFailed` message from the HTTP status plus a sanitized URL (password/username/query/fragment stripped) and a reqwest error category (builder/redirect/status/body/decode/request). `From<anyhow::Error>` walks the cause chain to recover a nested typed `ProviderError`, else a `reqwest::Error`, else a tokio `Elapsed` → `NetworkError`, else a generic `ExecutionError`. `from_stream_error` downcasts an anyhow error to a typed `ProviderError` or falls back to a retryable `NetworkError` stream-decode error.
**Invariant:** diagnostics never contain URL credentials (username/password stripped) or query secrets (query cleared); network errors carry a stable friendly message; the anyhow chain preserves a nested typed `ProviderError`; every variant has a stable `telemetry_type` tag; a stream decode failure maps to a retryable `NetworkError` rather than a fatal class.
**Probe:** `crates/goose-provider-types/src/errors.rs` `#[cfg(test)]` — `direct_reqwest_error_redacts_unsupported_scheme_url` (ftp URL with user:pass@ and query-secret → message keeps `ftp://provider.invalid/chat` but drops `query-secret`/`url-user`/`url-password`) and `anyhow_wrapped_status_error_redacts_url` (real local HTTP 401 → message keeps `status: 401 Unauthorized` and `http://{addr}/chat` but drops the credential parts). Verified GREEN via `cargo test -p goose-provider-types --lib errors` (errors tests pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "ProviderError telemetry_type provider_error_from_reqwest sanitized_reqwest_url from_stream_error", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the typed error taxonomy and the reqwest/anyhow→`ProviderError` mapping with credential-free URL sanitization (strip user/password/query/fragment), the cause-chain unwrap that preserves a nested typed error, and the stable `telemetry_type` tag per variant. Adapt the message wording and the network-classification predicates to the target HTTP client; keep the redaction invariant verbatim. Omit the `GoogleErrorCode` status-code helper and the provider-specific variants (`CreditsExhausted`/`Refusal`) when the target has no such concepts. Coverage: `crates/goose-provider-types/src/errors.rs` `no_recorded_issue` + `metadata_match`; cargo test runner available, direct tests pass.