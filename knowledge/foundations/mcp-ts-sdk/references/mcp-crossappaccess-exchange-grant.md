<!-- capsule-v2 -->
# exchangeJwtAuthGrant + discoverAndRequestJwtAuthGrant — how does the JAG become tokens, and who picks the client-auth method?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What is the default client authentication for the RFC 7523 leg, and where must IdP discovery happen before the exchange?

## JWT-bearer exchange with pluggable applyClientAuthentication + discovery wrapper
**Path/Symbol:** `packages/client/src/client/crossAppAccess.ts` `exchangeJwtAuthGrant` (:250-307) and `discoverAndRequestJwtAuthGrant` (:205-221); shared primitives in `packages/client/src/client/auth.ts`: `applyClientAuthentication` :776-801, `applyBasicAuth` :806-813 (throws on missing secret!), `applyPublicAuth` :828-830, `assertSecureTokenEndpoint` :841-847.
**Signature:** `exchangeJwtAuthGrant({ tokenEndpoint, jwtAuthGrant, clientId, clientSecret?, authMethod?: ClientAuthMethod = 'client_secret_basic', fetchFn? }) => Promise<{ access_token: string; token_type: string; expires_in?: number; scope?: string }>`; wrapper takes `{ idpUrl, … }` and discovers via `.well-known/oauth-authorization-server`.
**Data Shape:** Body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer`, `assertion=<JAG>`, optional `scope`; auth applied to Headers/Params by method — basic → Authorization header, post → body params, none → bare `client_id`.

### Decisive source
```ts
const { tokenEndpoint, jwtAuthGrant, clientId, clientSecret, authMethod = 'client_secret_basic', fetchFn = fetch } = options;
```
(:263 — default aligns with CrossAppAccessProvider's declared token_endpoint_auth_method and SEP-990 conformance; doc-comment says use 'client_secret_post' ONLY when the AS requires it, 'none' for public clients)

```ts
export function assertSecureTokenEndpoint(tokenEndpoint: string | URL): URL {
    const url = new URL(String(tokenEndpoint));
    if (url.protocol !== 'https:' && !isLoopbackHost(url.hostname)) {
        throw new InsecureTokenEndpointError(url.href);
    }
    return url;
}
```
(auth.ts:841-847; loopback = localhost/127.0.0.1/[::1]/::1 per :832-835)

**Flow:** Wrapper path: discover IdP metadata → missing `token_endpoint` throws `Failed to discover token endpoint for IdP: <idpUrl>` → delegate with resolved endpoint. Exchange path: TLS gate → build params → `applyClientAuthentication(authMethod, { client_id, client_secret }, headers, params)` (SHARED with the SDK's own token leg — one implementation serves both) → non-ok maps OAuth-typed errors (`JWT grant exchange failed: …`) else raw status → ok strict-parses `OAuthTokensSchema.safeParse` (access_token + token_type required there) → returns parsed data.
**Invariant:** `applyBasicAuth` THROWS `'client_secret_basic authentication requires a client_secret'` when the secret is falsy — so default-method + no-secret is a construction-time-adjacent loud failure, not a silent unauthenticated POST; public clients MUST pass `'none'` explicitly. The TLS gate runs in ALL THREE entry functions of this module before any credential materializes.
**Probe:** `grep -n "authMethod = " packages/client/src/client/crossAppAccess.ts` → single destructuring line :263; `grep -cF 'assertSecureTokenEndpoint' packages/client/src/client/crossAppAccess.ts` → 3 (import + two call sites :127/:265); direct tests describe `exchangeJwtAuthGrant` incl. SEP-2207 reject :332, basic-by-default :346, post-when-requested :387, none-public :414, schema-validate :461.
**Caveat:** none — anchors byte-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "applyClientAuthentication basic auth header btoa", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: default-basic-with-loud-missing-secret, explicit-none-for-public, one shared auth-application function, TLS-gate-first ordering. Adapt the error strings. Omit nothing from the gate ladder — each rung exists because a real misconfiguration produces it.
