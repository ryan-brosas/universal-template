<!-- capsule-v2 -->
# PKCE skip-local-validation boundary — when does the token endpoint verify the code_verifier itself, and when must it hand the verifier upstream untouched?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How should a token endpoint treat PKCE when the authorization code's challenge lives on a different server?

## Grant switch & verifier routing
**Path/Symbol:** `packages/server-legacy/src/auth/handlers/token.ts`: schemas (:30-45), rate limit 50/15min (:58-69), `authenticateClient` mount (:72), grant switch (:91-144).
**Signature:** `tokenHandler({ provider, rateLimit }): RequestHandler`; provider knobs `skipLocalPkceValidation?: boolean`, `challengeForAuthorizationCode(client, code): Promise<string>`.
**Data Shape:** `AuthorizationCodeGrantSchema = {code, code_verifier, redirect_uri?, resource?}`; `RefreshTokenGrantSchema = {refresh_token, scope?, resource?}`; unknown `grant_type` → `UnsupportedGrantTypeError`.

### Decisive source
```ts
// :100-118 the whole contract
const skipLocalPkceValidation = provider.skipLocalPkceValidation;
// Perform local PKCE validation unless explicitly skipped
// (e.g. to validate code_verifier in upstream server)
if (!skipLocalPkceValidation) {
    const codeChallenge = await provider.challengeForAuthorizationCode(client, code);
    if (!(await verifyChallenge(code_verifier, codeChallenge))) {
        throw new InvalidGrantError('code_verifier does not match the challenge');
    }
}
// Passes the code_verifier to the provider if PKCE validation didn't occur locally
const tokens = await provider.exchangeAuthorizationCode(
    client, code,
    skipLocalPkceValidation ? code_verifier : undefined,
    redirect_uri,
    resource ? new URL(resource) : undefined
);
```

**Flow:** POST only → CORS any-origin (web-based MCP clients) → urlencoded parse → rate limit → client authentication middleware → grant switch: `authorization_code` runs the PKCE branch above; `refresh_token` passes scopes split on `' '` and optional resource indicator; default throws. Errors map OAuthError→400 (ServerError→500) with `toResponseObject()`. The proxy provider sets `skipLocalPkceValidation = true` and returns `''` from `challengeForAuthorizationCode` (:148-152) — it stores nothing; the upstream AS owns the challenge.

**Invariant:** exactly ONE of {local verify, forward-verifier} may happen — skipping local validation AND dropping the verifier would let any bearer of the code exchange it (PKCE silently off); doing BOTH double-validates against an empty challenge and fails every request. The verifier is forwarded through the same parameter a local check would consume, so providers stay symmetric. Client secret expiry is checked in `authenticateClient` (`client_secret_expires_at < now` → invalid_client), NOT here.

**Probe (direct tests):** `packages/server-legacy/test/auth/handlers/token.test.ts` — :216 'verifies code_verifier against challenge', :294 'passes through code verifier when using proxy provider', :348 'passes through redirect_uri when using proxy provider', :152 'rejects unsupported grant types'; clientAuth.test.ts :105 'rejects request when client secret has expired'.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "skipLocalPkceValidation exchangeAuthorizationCode code_verifier", limit: 3 });
```

## Verdict
Adopt the either-forward-or-verify XOR and grant-schema split; adapt challenge storage to your code store; omit CORS-any if your clients are not browser-based.
