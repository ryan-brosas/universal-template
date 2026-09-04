<!-- capsule-v2 -->
# Scope selection, client-auth method, and the PKCE plane — how does the client pick scope, token-endpoint auth method, and build the /authorize URL?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What are the exact priority orders and gates for `determineScope`, `selectClientAuthMethod`, and `startAuthorization` (PKCE) on the client side?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/auth.ts`: `determineScope` (:1043-1072), `selectClientAuthMethod` (:723-760) + `applyClientAuthentication` (:776-801), `startAuthorization` (:1994-2061); constants `AUTHORIZATION_CODE_RESPONSE_TYPE='code'` / `AUTHORIZATION_CODE_CHALLENGE_METHOD='S256'` (:708-709). Graph nodes `…auth.determineScope` (graph :1020-1049), `…auth.selectClientAuthMethod` (graph :723-760), `…auth.startAuthorization` (graph :1956-2023) — docblock-inclusive drift, source pins win.
**Signature:** `determineScope({requestedScope?, resourceMetadata?, authServerMetadata?, clientMetadata}): string | undefined` · `selectClientAuthMethod(clientInformation, supportedMethods: string[]): ClientAuthMethod` · `startAuthorization(authorizationServerUrl, {metadata?, clientInformation, redirectUrl, scope?, state?, resource?}): Promise<{authorizationUrl: URL, codeVerifier: string}>`.
**Data Shape:** space-delimited scope strings; `ClientAuthMethod = 'client_secret_basic' | 'client_secret_post' | 'none'`; `supportedMethods` is `metadata.token_endpoint_auth_methods_supported ?? []` (empty = field omitted).

### Decisive source
```ts
// :1056-1069 — scope priority + SEP-2207 offline_access gate
let effectiveScope = requestedScope || resourceMetadata?.scopes_supported?.join(' ') || clientMetadata.scope;
if (
    effectiveScope &&
    authServerMetadata?.scopes_supported?.includes('offline_access') &&
    !effectiveScope.split(' ').includes('offline_access') &&
    clientMetadata.grant_types?.includes('refresh_token')
) {
    effectiveScope = `${effectiveScope} offline_access`;
}
// :729-743 — DCR hint wins when valid; empty supportedMethods ⇒ RFC 8414 §2 default
if ('token_endpoint_auth_method' in clientInformation && clientInformation.token_endpoint_auth_method &&
    isClientAuthMethod(clientInformation.token_endpoint_auth_method) &&
    (supportedMethods.length === 0 || supportedMethods.includes(clientInformation.token_endpoint_auth_method))) {
    return clientInformation.token_endpoint_auth_method;
}
if (supportedMethods.length === 0) {
    return hasClientSecret ? 'client_secret_basic' : 'none';
}
// :2016-2028 + :2049-2054 — S256-only PKCE; offline_access forces prompt=consent
if (!metadata.response_types_supported.includes(AUTHORIZATION_CODE_RESPONSE_TYPE)) {
    throw new Error(`Incompatible auth server: does not support response type ${AUTHORIZATION_CODE_RESPONSE_TYPE}`);
}
if (metadata.code_challenge_methods_supported &&
    !metadata.code_challenge_methods_supported.includes(AUTHORIZATION_CODE_CHALLENGE_METHOD)) {
    throw new Error(`Incompatible auth server: does not support code challenge method ${AUTHORIZATION_CODE_CHALLENGE_METHOD}`);
}
// …
if (scope?.split(' ').includes('offline_access')) {
    authorizationUrl.searchParams.append('prompt', 'consent');   // OIDC offline-access rule
}
```

**Flow:** determineScope: requested > PRM `scopes_supported.join(' ')` > `clientMetadata.scope` > omit; then append `offline_access` only through the four-way gate above. selectClientAuthMethod: DCR-returned `token_endpoint_auth_method` (when a valid method AND either supported-list empty or listed) > RFC 8414 §2 default when the field is omitted (`client_secret_basic` with secret, else `none`) > priority basic > post > none > fallback `hasSecret ? post : none`. startAuthorization: metadata present ⇒ use its `authorization_endpoint` after the two compatibility throws; absent ⇒ default `/authorize`; then set response_type/client_id/code_challenge(+S256)/redirect_uri and optional state/scope/resource; return `{authorizationUrl, codeVerifier}` — the caller (authInternal :1386) saves the verifier via `provider.saveCodeVerifier`.

**Invariant:** `offline_access` is appended ONLY when some other scope already exists (an offline-only request stays undefined — no gratuitous consent prompt), the AS advertises it, it is not already present, AND the CONSUMER-supplied `grant_types` includes `refresh_token` — the SDK's own DCR default is intentionally NOT applied here so statically-registered/CIMD clients are not pushed into offline_access + prompt=consent. S256 is the only accepted challenge method; an AS advertising other methods is rejected, while an AS omitting the field is trusted. `prompt=consent` is APPENDED (not set), so a host-provided prompt survives alongside it.

**Probe:** `packages/client/test/client/auth.test.ts` :4634-4705 (MCP Scope Selection Strategy matrix: explicit beats PRM beats clientMetadata.scope), :4706-4790+ (SEP-2207 matrix incl. "does NOT augment when no other scopes are present" ⇒ undefined, "does NOT augment when AS metadata lacks offline_access"), :1706-1745 (selectClientAuthMethod five-row table incl. RFC 8414 §2 default and DCR-hint-with-empty-metadata), :1773-1790 (PKCE URL params: response_type=code, code_challenge, code_challenge_method=S256, redirect_uri, resource), :1829-1840 (offline_access ⇒ prompt=consent).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "typescript-sdk", qualified_name: "typescript-sdk.packages.client.src.client.auth.startAuthorization" });
// or: search_graph({ project: "typescript-sdk", query: "determineScope selectClientAuthMethod startAuthorization", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all three as pure functions verbatim (no I/O inside; fetch happens in the callers); adapt the `grant_types` gate if your registration path always materializes grant_types server-side; omit any plan to support plain/other PKCE challenge methods — the SDK hard-rejects them, and loosening that without re-auditing the token-exchange side would break the verifier contract. Companion capsules: auth-main-flow-ladder.md (the caller), step-up-scope-union.md (scope widening on 403).
