<!-- capsule-v2 -->
# Bearer token gate — how do you verify an OAuth bearer token and answer every failure with the right HTTP challenge?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** A Resource Server must check `Authorization: Bearer …`, enforce scopes/expiry, and map each failure to status + `WWW-Authenticate` — what is the exact decision ladder and its ordering?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/middleware/bearerAuth.ts`: `verifyBearerToken` (:94-124), `bearerAuthChallengeResponse` (:136-163), `requireBearerAuth` fetch gate (:185-203), `headerQuotedValue`/`buildWwwAuthenticateHeader` (:57-79). Graph qn `typescript-sdk.packages.server.src.server.middleware.bearerAuth.verifyBearerToken` etc.
**Signature:** `verifyBearerToken(authorizationHeader: string|null|undefined, options: BearerAuthOptions): Promise<AuthInfo>`; `bearerAuthChallengeResponse(error: unknown, options?: Pick<BearerAuthOptions,'requiredScopes'|'resourceMetadataUrl'>): Response`; `requireBearerAuth(options): (request: Request) => Promise<AuthInfo | Response>`.
**Data Shape:** `BearerAuthOptions = {verifier: OAuthTokenVerifier; requiredScopes?: string[]; resourceMetadataUrl?: string}`; `OAuthTokenVerifier.verifyAccessToken(token): Promise<AuthInfo>` where `AuthInfo = {token, clientId, scopes: string[], expiresAt: number}`. Verifier throws `OAuthError(InvalidToken)` for unknown/revoked tokens.

### Decisive source
```ts
// ORDER IS THE CONTRACT: format → verifier → scopes → expiry.
const [type, token] = authorizationHeader.split(' ');
if (type?.toLowerCase() !== 'bearer' || !token) { throw new OAuthError(OAuthErrorCode.InvalidToken,
    "Invalid Authorization header format, expected 'Bearer TOKEN'"); }
const authInfo = await verifier.verifyAccessToken(token);
if (requiredScopes.length > 0) {
    const hasAllScopes = requiredScopes.every(scope => authInfo.scopes.includes(scope));
    if (!hasAllScopes) { throw new OAuthError(OAuthErrorCode.InsufficientScope, 'Insufficient scope'); }
}
// A token whose AuthInfo.expiresAt is UNSET is rejected outright (v1 parity):
// verifiers must populate it from introspection/JWT exp.
if (typeof authInfo.expiresAt !== 'number' || Number.isNaN(authInfo.expiresAt)) {
    throw new OAuthError(OAuthErrorCode.InvalidToken, 'Token has no expiration time');
} else if (authInfo.expiresAt < Date.now() / 1000) { throw new OAuthError(OAuthErrorCode.InvalidToken, 'Token has expired'); }
```

**Flow:** verify ladder emits typed `OAuthError`s → challenge mapper switches on `error.code`: non-OAuthError ⇒ synthesized `500 server_error` body; `invalid_token` ⇒ `401` + challenge header; `insufficient_scope` ⇒ `403` + challenge; `server_error` ⇒ `500` NO challenge; anything else ⇒ `400` NO challenge. Challenge string order is pinned by test: `error`, `error_description`, then `scope="…"` (space-joined, only when requiredScopes non-empty), then `resource_metadata="…"` last. The fetch gate resolves to `AuthInfo | Response` (never rejects): it takes the FIRST comma-segment of `headers.get('authorization')` because Fetch comma-joins repeated headers where Node keeps the first — lossless since the token68 alphabet has no comma — and destructures options at CREATION time so a malformed plain-JS call crashes at startup, not first request. Header-safety pre-pass (`headerQuotedValue`) escapes `\` and `"` and replaces any char outside `\u0020-\u007E` with a space, so a hostile verifier-authored error_description can never make the Response constructor throw or inject CR/LF into the challenge.

**Invariant:** Scope check runs BEFORE expiry ("expired AND missing scope ⇒ insufficient_scope wins" — matching the Express middleware order, pinned by test :65-72). Missing/unparsable `expiresAt` is invalid_token, never "valid forever". Only `invalid_token`/`insufficient_scope` carry `WWW-Authenticate`; server_error must not advertise auth requirements. The adapter boundary is exact: wrong-framework misuse (no web-standard Request) throws loudly OUTSIDE the try — it must not masquerade as a 500 challenge.

**Probe:** `packages/server/test/server/bearerAuth.test.ts` — :65 scope-before-expiry ordering, :74 missing-expiresAt rejection, :98 challenge field order incl. `resource_metadata` last, :119 500-without-challenge for ServerError, :125 400 default, :132 non-OAuthError ⇒ 500, :170/:176 hostile-message hardening, :193 duplicate-header comma-join first-wins, :204 creation-time TypeError. Express adapter mirror: `packages/middleware/express/test/auth/resourceServer.test.ts` :36/:55/:86/:103.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "verifyBearerToken bearerAuthChallengeResponse requireBearerAuth", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the four-rung ladder order, the code→status/challenge mapping table, expiresAt-required policy, quoted-string sanitization before header emission, and the AuthInfo|Response union gate shape. Adapt the express body derivation (adapter re-reads `WWW-Authenticate` off the core Response but rebuilds the JSON from the original OAuthError). Omit the legacy `packages/server-legacy` variant entirely — superseded shape.
