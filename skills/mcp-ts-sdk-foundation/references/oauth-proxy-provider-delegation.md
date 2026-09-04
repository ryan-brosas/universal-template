<!-- capsule-v2 -->
# Proxy OAuth server provider — how does a pass-through AS delegate every OAuth verb while keeping the SDK's handler contracts intact?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When your MCP server fronts an upstream authorization server, which responsibilities stay local and which move upstream — and how do the two flags that govern claims get set?

## Delegation matrix
**Path/Symbol:** `packages/server-legacy/src/auth/providers/proxyProvider.ts`: `ProxyOAuthServerProvider` (:42-244), flags (:48-59), conditional `revokeToken` assignment (:68-99), shape-conditional `clientsStore` (:102-126).
**Signature:** `new ProxyOAuthServerProvider({ endpoints: {authorizationUrl, tokenUrl, revocationUrl?, registrationUrl?}, verifyAccessToken, getClient, fetch? })`.
**Data Shape:** upstream responses parsed through shared zod schemas (`OAuthTokensSchema.parse`, `OAuthClientInformationFullSchema.parse`) so wire drift fails LOUDLY at the proxy; all HTTP via injectable `FetchLike` (`this._fetch ?? fetch`).

### Decisive source
```ts
// :48-59 both posture flags side by side
skipLocalPkceValidation = true;
/**
 * The proxy redirects the browser to the upstream AS's authorize endpoint with
 * `redirect_uri = params.redirectUri`, so the upstream — not this proxy — issues the
 * callback. The proxy cannot append its own `iss`… Advertise `false` so the metadata
 * does not over-claim — a callback *without* `iss` then passes validation.
 */
authorizationResponseIssParameterSupported = false;
```

**Flow:** authorize → 302 to upstream authorizationUrl with client_id/response_type/redirect_uri/code_challenge/S256 (+state/scope/resource) — the ISS wrapper from oauth-iss-redirect-monkey-patch leaves this redirect untouched (different origin/path). exchangeAuthorizationCode / exchangeRefreshToken → form-encoded POST to tokenUrl, secret appended when present, response schema-parsed. revokeToken exists ONLY when `endpoints.revocationUrl` was configured (assigned in constructor); clientsStore.registerClient exists ONLY when `registrationUrl` is set — the router reads these shapes to derive metadata endpoints (oauth-router-metadata-construction). challengeForAuthorizationCode returns `''` (stores nothing).

**Invariant:** a proxy must retract BOTH claims it cannot enforce: `skipLocalPkceValidation=true` (no local challenge) AND `authorizationResponseIssParameterSupported=false` (not the callback issuer) — flipping either on produces a server that rejects every PKCE exchange or over-claims RFC 9207 support. Upstream non-2xx becomes a LOCAL `ServerError` ("Token exchange failed: <status>") after cancelling the body — the client never sees raw upstream errors.

**Probe (direct tests):** `packages/server-legacy/test/auth/providers/proxyProvider.test.ts` (352L) — pins authorize URL construction, code-verifier/redirect_uri passthrough (token.test.ts :294/:348 ride this provider), revocation gating on configured endpoint.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "ProxyOAuthServerProvider skipLocalPkceValidation endpoints", limit: 3 });
```

## Verdict
Adopt the delegation matrix and claim-retraction pairing; adapt endpoint config and fetch injection to your platform; omit the schema-parse step only if your upstream is contract-tested by you.
