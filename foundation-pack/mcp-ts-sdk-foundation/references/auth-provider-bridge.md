<!-- capsule-v2 -->
# AuthProvider SPI bridge — how do transports accept both an API-key lambda and a full OAuth provider through one interface?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** How is a minimal `{ token }` provider distinguished from an `OAuthClientProvider`, and what does the adaptation preserve (and deliberately skip) at the transport boundary?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/auth.ts`: `AuthProvider` (:76-92), `isOAuthClientProvider` (:166-170), `handleOAuthUnauthorized` (:177-193), `adaptOAuthProvider` (:210-221), `OAuthClientInformationContext` issuer-keyed storage contract (:102-108, :284-305); callers (graph trace): BOTH `SSEClientTransport.constructor` and `StreamableHTTPClientTransport.constructor`.
**Signature:** `isOAuthClientProvider(p: AuthProvider | OAuthClientProvider | undefined): p is OAuthClientProvider` · `adaptOAuthProvider(provider: OAuthClientProvider, extraAuthOptions?): AuthProvider`
**Data Shape:** minimal SPI = `{ token(): Promise<string|undefined>; onUnauthorized?(ctx): Promise<void> }`; ctx = `{ response, serverUrl, fetchFn }`.

### Decisive source
```ts
// :166-170 — duck-type on two methods a minimal provider can never have
const p = provider as OAuthClientProvider;
return typeof p.tokens === 'function' && typeof p.clientInformation === 'function';
// :214-220 — the bridge; token() carries NO issuer context
return {
    token: async () => { const tokens = await provider.tokens(); return tokens?.access_token; },
    onUnauthorized: async ctx => handleOAuthUnauthorized(provider, ctx, extraAuthOptions)
};
// handleOAuthUnauthorized (:177-193): extractWWWAuthenticateParams → auth(); result !== 'AUTHORIZED' ⇒ UnauthorizedError
```

**Flow:** transport constructor classifies `authProvider` once (`isOAuthClientProvider`) → stores
the ADAPTED provider for `_commonHeaders()` bearer reads + 401 handling while keeping the ORIGINAL
for OAuth-specific paths (`finishAuth()`, 403 step-up) → 401 ⇒ `handleOAuthUnauthorized` =
extract challenge params → `auth()` → result ≠ `'AUTHORIZED'` ⇒ `UnauthorizedError`.

**Invariant:** the adapted `token()` runs BEFORE any discovery has happened, so it passes no
issuer ctx — per the SEP-2352 contract, providers keying storage on `ctx.issuer` MUST treat
`ctx === undefined` as "return the most-recently-saved token set" (the only consumer is the
resource server the token was minted for); the access token goes only to the resource server, so
cross-AS isolation is out of scope at this seam. The adapter is built ONCE at construction —
per-request state lives in the provider, not the wrapper.

**Probe:** `packages/client/test/client/tokenProvider.test.ts` exercises provider-shaped options;
source-level probe: both transport constructors call `adaptOAuthProvider` (trace_path shows exactly
2 callers). Direct behavioral test of the bridge itself rides the 401 restart chains cited in
sse-client-endpoint-bracket.md / client-send-ladder.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "typescript-sdk", function_name: "adaptOAuthProvider", direction: "both" });
```

## Verdict
Adopt the two-shape SPI + duck-type classification for any pluggable credential surface; adapt
`onUnauthorized`'s retry-once policy to your host's backoff needs; omit the SEP-2352
no-ctx exemption only if every consumer of your provider is post-discovery. Deepens auth.md's
pass-1 loose pins with the exact-range bridge contract.
