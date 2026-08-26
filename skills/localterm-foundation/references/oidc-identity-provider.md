<!-- capsule-v2 -->
# OIDC identity provider — bring-your-own-IdP authorization-code + PKCE without an auth framework

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you add Google/Authentik/Zitadel login to a Hono daemon with oauth4webapi primitives and keep every failure path safe?

## Consume-once state entries + two-character open-redirect defense + self-healing discovery cache
**Path/Symbol:** `packages/server/src/identity/oidc-provider.ts` — `OidcStateStore` (:26–43), `sanitizeReturnTo` (:48–51), `buildOidcRoutes` (:68–183), `createOidcIdentityProvider` (:191–239).
**Data Shape:** state entry `{ codeVerifier, nonce, returnTo, expiresAt }`, TTL 10 min (`AUTH_STATE_TTL_MS`), in-memory Map keyed by the OIDC `state`. Client auth: `clientSecret ? oauth.ClientSecretPost(secret) : oauth.None()` (public PKCE-only client).

### Decisive source
```ts
// Only allow same-origin relative paths as the post-login landing target, to
// keep the callback from being an open redirect: a value must start with `/`
// and not `//` (a protocol-relative URL the browser would treat as absolute).
export const sanitizeReturnTo = (value: string | null): string => {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/";
  return value;
};
```
And the discovery cache that never caches failure:
```ts
let metadataPromise: Promise<AuthorizationServer> | null = null;
const getMetadata = (): Promise<AuthorizationServer> => {
    if (!metadataPromise) {
      metadataPromise = (async () =>
        oauth.processDiscoveryResponse(issuerUrl, await oauth.discoveryRequest(issuerUrl)))();
      metadataPromise.catch(() => {
        metadataPromise = null;
      });
    }
    return metadataPromise;
  };
```

**Flow:** /oidc/login?returnTo= → require announced origin (else 500 BEFORE any network call) → discovery → mint PKCE verifier+S256 challenge, random state+nonce → store {verifier, nonce, sanitized returnTo} against state → 302 to the IdP authorization_endpoint with client_id/redirect_uri/response_type=code/scope/state/nonce/code_challenge. Callback: consume(state) (single-use, expired → "/"), validateAuthResponse against state, authorizationCodeGrantRequest with the stored verifier, processAuthorizationCodeResponse with expectedNonce, processUserInfoResponse, identity = userInfo[claim] (default email) falling back to sub, clamped to 256 chars → session cookie → 302 returnTo. Every catch redirects "/" — error pages never leak to the browser.
**Invariant:** redirect_uri is announced-origin + `/auth/oidc/callback` and must be pre-registered with the IdP, so OIDC needs a STABLE announced origin — unlike passkey which binds to whatever origin the browser is on. State/PKCE/nonce live together in ONE entry so they can't be mixed across flows; consumption deletes before validating, so a replayed callback URL fails even against a warm store.
**Probe:** `packages/server/tests/oidc.test.ts` — schema accepts minimal/full :25–40, rejects non-URL issuer/missing clientId :42–49, rejects extra keys (strict) :51–60; sanitizeReturnTo allows "/sessions","/" :64–67 and blocks "//evil.com", "https://evil.com", null, "" :69–74; denyUnauthenticated true :87–91; login 500s on missing origin pre-network :93–103; /auth/oidc/me reads out-of-band cookie :105–122 and null without :124–130; logout clears with Max-Age=0 :132–142. Executed this pass, green.
**Retrieve (executed live):**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "OidcStateStore|sanitizeReturnTo|buildOidcRoutes|createOidcIdentityProvider", limit: 10 });
```

## Verdict
Adopt: one Map entry per flow holding verifier+nonce+returnTo with consume-once semantics; the starts-with-/ and-not-// redirect sanitizer; the promise-slot discovery cache that resets on rejection; catch-all redirect-to-/ callbacks. Adapt claim/scope defaults and client-auth selection to your IdPs; omit token-refresh machinery — sessions are local cookies, the IdP token is discarded after userinfo. Trap: validating state AFTER consuming is right, but validating it against a value still in the map (non-deleting read) invites replay; and returning error pages from callback catches leaks issuer internals.
