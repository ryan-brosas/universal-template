<!-- capsule-v2 -->
# RFC 8628 device flow — how do you poll a token endpoint whose pending/slow_down answers arrive as HTTP 4xx JSON bodies, tolerate omitted fields, and keep the user announce swappable?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how do you implement device-authorization polling and refresh that survive real-server quirks (4xx-carried RFC errors, missing `interval`/`expires_in`/`refresh_token`) while letting an embedding UI replace the CLI announce?

## Parse-before-status poll loop + RFC tolerance defaults
**Path/Symbol:** `crates/goose/src/providers/oauth_device_flow.rs` — `DeviceFlowConfig` (51–65), `DEVICE_CODE_ANNOUNCE` task-local + `with_device_code_announce` (14–29), fallback consts 5s/300s/+5s (31–38), `request_device_code` (111–138), `poll_for_tokens` (142–192), `run_device_flow` (196–209), `refresh_device_flow_token` (212–260), `TokenResponseBody`/`TokenPollOutcome`/`parse_token_response` (264–318).
**Signature:** `async fn poll_for_tokens(client: &Client, cfg: &DeviceFlowConfig<'_>, device_code: &str, interval_secs: u64, expires_in_secs: u64) -> Result<DeviceFlowTokens>`; `enum TokenPollOutcome { Issued(DeviceFlowTokens), Pending, SlowDown, Failed(String) }`; `struct DeviceFlowTokens { access_token: String, refresh_token: Option<String>, expires_at: Option<DateTime<Utc>> }`.
**Data Shape:** `DeviceCodeResponse{device_code, user_code, verification_uri, verification_uri_complete?, interval?, expires_in?}` with `verification_url()` preferring the `_complete` form; requests encode as Form (RFC §3.1) or Json (GitHub quirk) per `RequestEncoding`; extra headers ride along on every call.

### Decisive source
```rust
// oauth_device_flow.rs — RFC 8628 §3.5 delivers authorization_pending /
// slow_down as HTTP 4xx WITH a JSON body, so classify the PARSED body before
// any status check; slow_down grows the effective interval by +5 seconds.
match parse_token_response(response).await? {
    TokenPollOutcome::Issued(tokens) => return Ok(tokens),
    TokenPollOutcome::Pending => { /* keep polling */ }
    TokenPollOutcome::SlowDown => { effective_interval += SLOW_DOWN_BACKOFF_SECS; }
    TokenPollOutcome::Failed(err) => return Err(anyhow!("authorization failed: {}", err)),
}
```

**Flow:** `request_device_code` POSTs `{client_id, scope?}` and — unlike polling — DOES call `error_for_status()` before parsing, because device-auth failures are plain HTTP → `announce_user_action` prefers the tokio task-local `DEVICE_CODE_ANNOUNCE` hook (set by ACP/desktop via `with_device_code_announce`), else clipboard-copies the code, opens `verification_url()`, and prints instructions to STDERR (stdout stays parseable) → poll loop checks the deadline, sleeps `effective_interval`, sends, then parses FIRST: Issued / Pending / SlowDown(+5s) / Failed; a 4xx with UNPARSEABLE body surfaces raw `HTTP {status}: {body}` instead of a generic parse error → `run_device_flow` falls back to 5s interval / 300s lifetime when the server omits either (§3.2) → `refresh_device_flow_token` reads bytes and parses BEFORE checking status; non-success becomes typed `DeviceFlowTokenRefreshError{status, error, body}`; success requires `access_token`, passes `refresh_token` through verbatim (server MAY omit it, RFC 6749 §6 — caller must reuse the prior one), and derives `expires_at` only when `expires_in` is present.
**Invariant:** pending/slow_down classification never depends on the HTTP status class; unparseable non-2xx bodies still yield status+body detail; deadline expiry yields "timed out waiting for user authorization"; announce replacement is scoped per-flow via task-local rather than global configuration.
**Probe:** `cargo test -p goose --lib oauth_device_flow` — observed GREEN 9 passed / 0 failed: poll_returns_issued_tokens_when_server_responds_immediately, poll_handles_authorization_pending_then_success, poll_handles_slow_down_then_success, poll_times_out_when_user_never_authorizes, poll_surfaces_http_status_on_unparseable_body, poll_surfaces_server_error_message, request_device_code_parses_complete_response, refresh_token_returns_new_credentials, refresh_token_allows_server_to_omit_refresh_token. (Corrects the work-record note of "10 wiremock tests": the file contains exactly 9.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "request_device_code poll_for_tokens refresh_access_token device code flow", limit: 12 });
// located: oauth_device_flow.rs request_device_code 111-138, poll_for_tokens 142-192, run_device_flow 196-209,
// refresh_device_flow_token 212-260, with_device_code_announce 21-29, DeviceCodeResponse struct;
// consumers: kimicode.rs device_flow_login 289-302; NOTE xai_oauth.rs 293-314 is a separate divergent copy
```

## Verdict
Adopt parse-before-status classification, the +5s slow-down ladder, 5s/300s omitted-field fallbacks, the keep-prior-refresh-token rule, typed refresh errors carrying status+body, the task-local announce seam, and the Form|Json encoding switch. Adapt endpoints, client IDs, headers, and encoding per provider (kimicode and githubcopilot consume this helper). Omit arboard/webbrowser CLI ergonomics in headless hosts — that is exactly what the announce hook replaces. Beware: `xai_oauth.rs` forks its own device flow; port THIS shared module, not the fork. Coverage: oauth_device_flow.rs `no_recorded_issue` + `metadata_match`; direct tests GREEN.
