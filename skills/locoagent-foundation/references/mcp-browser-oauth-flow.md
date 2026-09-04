<!-- capsule-v2 -->
# Browser OAuth flow hardening — how do I run the localhost callback dance against CSRF, XSS-in-error, port conflicts, and event-loop pinning?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What does a production-grade authorization-code flow around a local callback HTTP server look like?

## State validation, xss-sanitized error pages, unref'd server+timer, paste-fallback
**Path/Symbol:** `src/services/mcp/auth.ts`:`performMCPOAuthFlow` (:847-1342): cached step-up scope read BEFORE clearing tokens (:903-935), callback promise with resolveOnce/rejectOnce latch (:1029-1041), state checks (:1079-1084 manual-paste path; :1109-1117 server path), xss sanitization (:1120-1139), EADDRINUSE diagnostics (:1153-1169), unref discipline (:1198-1213), 5-minute timeout (:1204-1213), failure-reason attribution ladder (:1259-1291), invalid_client recovery (:1305-1318).
**Signature:** `performMCPOAuthFlow(serverName, serverConfig, onAuthorizationUrl, abortSignal?, options?: {skipBrowserOpen?, onWaitingForCallback?}): Promise<void>`.
**Data Shape:** SENSITIVE_OAUTH_PARAMS = [state, nonce, code_challenge, code_verifier, code] redacted via `redactSensitiveUrlParams` before ANY URL is logged (:100-125).

### Decisive source
```ts
// Validate OAuth state to prevent CSRF attacks
if (!error && state !== oauthState) {
  res.writeHead(400, { 'Content-Type': 'text/html' })
  res.end(`<h1>Authentication Error</h1><p>Invalid state parameter. Please try again.</p>...`)
  cleanup(); rejectOnce(new Error('OAuth state mismatch - possible CSRF attack')); return
}
if (error) {
  // Sanitize error messages to prevent XSS — provider-controlled strings go into HTML
  const sanitizedError = xss(String(error))
  ...
}
server.unref()      // "Don't let the callback server or timeout pin the event loop...
timeoutId.unref()   //  we'd rather let the process exit than stay alive for 5 minutes holding the port."
// abortSignal is the intended lifecycle management; abortHandler runs cleanup()
```

**Flow:** clear stored credentials (fresh DCR), preserving previously-cached stepUpScope/resourceMetadataUrl read beforehand → findAvailablePort (config oauth.callbackPort wins; see registry+ports capsule) → create ClaudeAuthProvider with handleRedirection=true → fetch AS metadata for scope → start local server on 127.0.0.1 → sdkAuth() first call expects REDIRECT → browser/paste delivers code+state → validate → second sdkAuth call exchanges code → 'AUTHORIZED' ⇒ verify tokens present. Failure attribution maps message patterns to stable reason codes (cancelled/timeout/state_mismatch/provider_denied/port_unavailable/sdk_auth_failed/token_exchange_failed) using the `authorizationCodeObtained` flag to distinguish exchange-phase failures (:954-956,:1271).
**Invariant:** Every exit path funnels through cleanup() (removeAllListeners + defensive error swallow + close server + clearTimeout + removeEventListener) and resolveOnce/rejectOnce guarantees single settlement; state mismatch on EITHER intake path aborts the whole flow.
**Probe:** `grep -c 'state !== oauthState' src/services/mcp/auth.ts` (`2`) and `grep -n 'server.unref()' src/services/mcp/auth.ts | head -1` (`1202:`) and `grep -nF 'xss(String(error))' src/services/mcp/auth.ts` (`1123:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "performMCPOAuthFlow", limit: 5 });
```

## Verdict
Adopt the latch+cleanup structure, dual-intake state validation, XSS-sanitized provider errors, unref'd lifecycle, and reason-attribution telemetry taxonomy. Adapt port/UX details.
