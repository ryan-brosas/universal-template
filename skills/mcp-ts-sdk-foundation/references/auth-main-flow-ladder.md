<!-- capsule-v2 -->
# auth() main flow — how does the client-side OAuth orchestrator decide discovery-vs-cache, gate the callback leg, and branch exchange/refresh/redirect?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What is the exact decision ladder of `auth()`/`authInternal` — which state is restored from cache, when is fresh discovery persisted, and which failures retry vs rethrow?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/auth.ts`: `auth` (:1014-1038), `warnCredentialInvalidation` (:994-1006), `authInternal` (:1074-1389); graph node `typescript-sdk.packages.client.src.client.auth.authInternal` (graph range :1051-1351 — docblock-inclusive drift, source pins win). Companion seams: auth.md (SEP-2352 stamp mechanics), refresh-persistence-boundary.md (:1326-1373 slice), oauth-callback-error-gate.md (callback param gate).
**Signature:** `auth(provider: OAuthClientProvider, options: AuthOptions): Promise<AuthResult>` where `AuthResult = 'AUTHORIZED' | 'REDIRECT'`.
**Data Shape:** `AuthOptions { serverUrl, authorizationCode?, iss?, scope?, resourceMetadataUrl?, fetchFn?, skipIssuerMetadataValidation?, forceReauthorization? }`; provider SPI reads/writes discoveryState, clientInformation, tokens, codeVerifier; every stored credential carries an `issuer` stamp (SEP-2352).

### Decisive source
```ts
// :1014-1038 — auth() is a thin retry wrapper; ONLY OAuthError codes retry, once
export async function auth(provider: OAuthClientProvider, options: AuthOptions): Promise<AuthResult> {
    try {
        return await authInternal(provider, options);
    } catch (error) {
        if (error instanceof OAuthError) {
            if (error.code === OAuthErrorCode.InvalidClient || error.code === OAuthErrorCode.UnauthorizedClient) {
                warnCredentialInvalidation(provider, error, 'client credentials and tokens');
                // Not 'all' — preserve discoveryState so the callback-leg gate on retry doesn't
                // fire a false 'discoveryState was not available on the callback leg' AuthorizationServerMismatchError
                await provider.invalidateCredentials?.('client');
                await provider.invalidateCredentials?.('tokens');
                return await authInternal(provider, options);
            } else if (error.code === OAuthErrorCode.InvalidGrant) {
                warnCredentialInvalidation(provider, error, 'tokens');
                await provider.invalidateCredentials?.('tokens');
                return await authInternal(provider, options);
            }
        }
        throw error;
    }
}
// :1188-1205 — SEP-2352 callback-leg gate: fail-closed when the provider persists discoveryState
if (authorizationCode !== undefined) {
    const recordedIssuer = cachedState?.authorizationServerMetadata?.issuer ?? cachedState?.authorizationServerUrl;
    if (recordedIssuer === undefined) {
        if (provider.saveDiscoveryState !== undefined) {
            throw new AuthorizationServerMismatchError(
                'discoveryState was not available on the callback leg; ensure your provider persists discoveryState alongside codeVerifier',
                issuer);
        }
        console.warn('[mcp-sdk] OAuthClientProvider does not implement saveDiscoveryState()/discoveryState(); …');
    } else if (!issuersMatch(recordedIssuer, issuer)) {
        throw new AuthorizationServerMismatchError(recordedIssuer, issuer);
    }
}
// :1328-1362 — refresh branch: config errors rethrow, server errors fall through to fresh auth
if (tokens?.refresh_token && !forceReauthorization) {
    let newTokens: OAuthTokens | undefined;
    try {
        newTokens = await refreshAuthorization(authorizationServerUrl, { … });
    } catch (error) {
        if (error instanceof InsecureTokenEndpointError) throw error;   // re-auth cannot fix a misconfig
        if (!(error instanceof OAuthError) || error.code === OAuthErrorCode.ServerError) {
            console.warn(`[mcp-sdk] Could not refresh OAuth tokens; falling back to a new authorization request. Cause: ${JSON.stringify(…)}`);
        } else {
            throw error;   // invalid_grant etc. → outer wrapper retries after invalidation
        }
    }
    if (newTokens) { await provider.saveTokens({ ...newTokens, issuer }, infoCtx); return 'AUTHORIZED'; }
}
```

**Flow:** 1) `resolveClientMetadata` (spec defaults for the DCR body). 2) Discovery: cached `discoveryState.authorizationServerUrl` ⇒ restore + lazily fetch missing AS metadata + fetch PRM only if missing (`TypeError` propagates — network failure is not masked; RFC 9728-absent is swallowed) + re-save only if enriched; else full `discoverOAuthServerInfo`, capturing `freshDiscoveryState` but persisting it ONLY AFTER the callback-leg gate (a gate throw must not leave a freshly resolved, potentially PRM-poisoned AS recorded for the retry to read back as `recordedIssuer`). 3) Callback-leg gate (above) keyed on `authorizationCode`. 4) Client-info resolution: `discardIfIssuerMismatch` (mismatched stamp reads back undefined ⇒ re-register); static-credential mismatch ⇒ typed `AuthorizationServerMismatchError`; unstamped legacy value ⇒ back-stamp `{…info, issuer}` + save; no info + code present ⇒ hard Error; else SEP-991 URL-based client id or DCR via `registerClient`. 5) Branch: `authorizationCode || !provider.redirectUrl` ⇒ RFC 9207 `iss` validation (only when a code exists) ⇒ `fetchToken` ⇒ `saveTokens({...tokens, issuer})` ⇒ `'AUTHORIZED'`; else refresh branch (above) or `startAuthorization` ⇒ `saveCodeVerifier` ⇒ `redirectToAuthorization` ⇒ `'REDIRECT'`.

**Invariant:** the in-flight `authorization_code` + PKCE `code_verifier` are bound to the AS that minted them — a provider that implements `saveDiscoveryState` but returns no state on the callback leg MUST fail closed (fresh discovery may have resolved a different AS than the user approved at /authorize); providers without `saveDiscoveryState` keep legacy warn-and-proceed. Retry invalidates `'client'` before `'tokens'` and never `'all'` (discoveryState survives so the gate cannot mask the real `invalid_client`). Refresh-failure fallthrough to fresh authorization is deliberate but must be logged with JSON-stringified cause (AS-supplied bytes are attacker-controllable); `saveTokens` after a successful refresh must propagate (the AS may have rotated the refresh token).

**Probe:** `packages/client/test/client/auth.test.ts` :3134-3161 (invalid_grant with no invalidateCredentials: dead token replayed twice, warn says "without discarding", no redirect started), :3176-3197 (newline-forged AS error text stays one log line, `\n` escaped), :3213-3232 (invalid_client/unauthorized_client each invalidate 'client' AND 'tokens', resolves REDIRECT), :5047-5062 (gate throws on recorded-vs-resolved issuer difference), :5064-5085 (fail-closed: token endpoint never called, message names the missing discoveryState), :5087-5102 (no-discoveryState provider warns exactly once), :5104-5124 (back-stamp: legacy value used not re-registered, registerCalls 0), :5139-5171 (saveDiscoveryState NOT called when the gate throws — both fresh-discovery and cached-record cases), :5192-5218 (invalid_client on code exchange does not surface AuthorizationServerMismatchError).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "typescript-sdk", qualified_name: "typescript-sdk.packages.client.src.client.auth.authInternal" });
// or: search_graph({ project: "typescript-sdk", query: "authInternal discoverOAuthServerInfo saveDiscoveryState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrapper/ladder split (pure decision ladder inside, bounded single retry outside) and the fail-closed callback-leg gate verbatim; adapt the provider SPI to your host's storage (the gate's strength depends on discoveryState being persisted alongside codeVerifier across page navigation); omit the legacy warn-and-proceed path for new providers — it exists only for pre-SEP-2352 compatibility. Coverage caveat: graph line ranges for this file drift ~20 lines from source (docblock-inclusive); pin ranges from the file read.
