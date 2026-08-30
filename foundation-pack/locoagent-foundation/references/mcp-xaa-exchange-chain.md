<!-- capsule-v2 -->
# XAA two-leg exchange and discovery mix-up protection — how do I implement SEP-990 Cross-App Access (id_token → ID-JAG → access_token) safely?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What are the RFC 8693/7523 request shapes, validation gates, and AS-failover rules for token exchange without a browser?

## Four Layer-2 ops + one Layer-3 orchestrator
**Path/Symbol:** `src/services/mcp/xaa.ts`: consts (:31-34), `discoverProtectedResource` (:135-165), `discoverAuthorizationServer` (:178-210), `requestJwtAuthorizationGrant` (:233-310), `exchangeJwtAuthGrant` (:337-394), orchestrator `performCrossAppAccess` (:426-511); redaction `SENSITIVE_TOKEN_RE`/:redactTokens (:91-97).
**Signature:** grants `urn:ietf:params:oauth:grant-type:token-exchange` (subject_token=idToken, subject_token_type=id_token, requested_token_type=id-jag, audience=AS issuer, resource=PRM resource); jwt-bearer `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=<ID-JAG>` with default auth method `client_secret_basic`.
**Data Shape:** TokenExchangeResponseSchema tolerates string expires_in (`z.coerce.number()` — PHP-backed IdPs, :105-107); JwtBearerResponseSchema defaults token_type to 'Bearer' because many ASes omit it (:114-117).

### Decisive source
```ts
if (result.issued_token_type !== ID_JAG_TOKEN_TYPE) {
  throw new XaaTokenExchangeError(`...unexpected issued_token_type...`, true)
}
...
// RFC 8414 §3.3 / RFC 9728 §3 require HTTPS. A PRM-advertised http:// AS
// that self-consistently reports an http:// issuer would pass the mismatch
// check above, then we'd POST id_token + client_secret over plaintext.
if (new URL(meta.token_endpoint).protocol !== 'https:') {
  throw new Error(`XAA: refusing non-HTTPS token endpoint: ${meta.token_endpoint}`)
}
// PRM resource mismatch + AS issuer mismatch both validated by normalizeUrl()
// comparison (RFC 3986 §6.2.2 syntax normalization via URL roundtrip) (:156,:190)
...
const shouldClear = res.status < 500   // 4xx → id_token rejected, clear cache;
                                       // 5xx → IdP outage, id_token may still be valid, preserve
```

**Flow:** PRM discovery (validate resource == serverUrl, authorization_servers[0] present) → for EACH advertised AS in order: metadata discovery + issuer match + jwt-bearer grant support check (`grant_types_supported` is OPTIONAL per RFC 8414 §2 — only skip if the list EXPLICITLY omits jwt-bearer :441-443); collect per-AS errors into one aggregate message → pick auth method from advertised `token_endpoint_auth_methods_supported` (default basic; post only if basic absent AND post present :475-481) → ID-JAG at IdP → access_token at AS → return `{...tokens, authorizationServerUrl}` which callers MUST persist as discoveryState.authorizationServerUrl because refresh/revocation need the AS URL (MCP URL ≠ AS URL).
**Invariant:** issued_token_type must equal the ID-JAG URN; non-JSON exchange response = captive portal ⇒ shouldClear=false; every error body passes redactTokens before logging (a misbehaving AS echoing subject_token/client_secret must not leak into debug logs :86-90).
**Probe:** `grep -n 'urn:ietf:params:oauth:token-type:id-jag' src/services/mcp/xaa.ts` (`33:`) and `grep -n 'issued_token_type !== ID_JAG_TOKEN_TYPE' src/services/mcp/xaa.ts` (`299:`) and `grep -n \"new URL(meta.token_endpoint).protocol !== 'https:'\" src/services/mcp/xaa.ts` (`198:`) and `grep -n 'res.status < 500' src/services/mcp/xaa.ts` (`269:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "requestJwtAuthorizationGrant", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "discoverProtectedResource", limit: 5 });
```

## Verdict
Adopt the Layer-2 op shapes, mismatch/HTTPS validations, explicit-list-only AS skipping, and error-classification-driven id_token clearing. Adapt schema strictness. Omit conformance-script references.
