<!-- capsule-v2 -->
# Authorization-callback error gate — how do you surface an OAuth error redirect without leaking attacker-controlled text from a mix-up?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** In what order are `iss`, `code`, and callback `error` parameters validated so error text is only ever surfaced after the issuer is proven?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/auth.ts`: `resolveAuthorizationCallbackParams` (:657-700), `validateAuthorizationResponseIssuer` (:555-583), `isIssParameterSupported` (:551-553); callers (graph): both transports' `finishAuth`, example CLI `completeAuthorizationWithBrowser`; callees: `discoverOAuthServerInfo`, `discoverAuthorizationServerMetadata`, `IssuerMismatchError`, `OAuthError`, `UnauthorizedError`.
**Signature:** `resolveAuthorizationCallbackParams(codeOrParams: string | URLSearchParams, iss: string | undefined, provider: OAuthClientProvider, serverUrl: string | URL, opts?): Promise<{ authorizationCode: string; iss: string | undefined }>`
**Data Shape:** callback carries `code` / `iss` / `error` + `error_description` + `error_uri` query params.

### Decisive source
```ts
// :669-671 — truthy check: ?code= (empty string) is NO code, not a code
const code = codeOrParams.get('code');
if (code) {
    return { authorizationCode: code, iss: issParam };
}
// :675-688 — establish an authentic issuer baseline BEFORE reading error params
const discoveryState = await provider.discoveryState?.();
let metadata = discoveryState?.authorizationServerMetadata;
if (!metadata) { try { metadata = (await discoverOAuthServerInfo(serverUrl, opts)).authorizationServerMetadata; } catch { metadata = undefined; } }
if (!metadata) {
    // No authentic baseline → cannot prove the error params came from our AS. Do NOT surface
    throw new UnauthorizedError('Authorization callback failed and the issuer could not be verified');
}
// :690-697 — four-row RFC 9207 table, THEN the gated OAuthError
validateAuthorizationResponseIssuer({ iss: issParam, expectedIssuer: metadata.issuer, issParameterSupported: isIssParameterSupported(metadata) });
if (error) { throw new OAuthError(error, codeOrParams.get('error_description') ?? error, codeOrParams.get('error_uri') ?? undefined); }
```

**Flow:** `(code, iss?)` string overload passes straight through (validation deferred to `auth()`
against fresh metadata). Params overload: `code` present ⇒ return for redemption; else
error-shaped ⇒ resolve baseline (provider `discoveryState()` → fresh discovery with swallowed
errors → none ⇒ generic `UnauthorizedError`) → run the four-row issuer check → only then throw
`OAuthError(error, description, uri)`; neither code nor error ⇒ `UnauthorizedError`.

**Invariant:** attacker-controlled `error*` strings can never reach the caller before the callback
issuer matches validated AS metadata — on mismatch (`IssuerMismatchError`) or unverifiable issuer,
the thrown error carries NONE of the callback's text. The issuer comparison is simple string
equality (RFC 3986 §6.2.1): no case folding, default-port elision, trailing-slash, or
percent-encoding normalization — any difference is a mismatch. `expectedIssuer === undefined`
(no validated metadata) degenerates to a no-op row-4 pass-through. Only a literal
`authorization_response_iss_parameter_supported === true` counts as advertised.

**Probe:** `packages/client/test/client/auth.test.ts` :1295-1332 — empty `?code=` falls through to
the error/neither diagnostic (truthy-check regression), `?code=&error=access_denied&iss=…` throws
the GATED `OAuthError`, `?code=abc&iss=…` resolves `{authorizationCode:'abc', iss}`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "typescript-sdk", qualified_name: "typescript-sdk.packages.client.src.client.auth.resolveAuthorizationCallbackParams" });
```

## Verdict
Adopt the gate-before-surface ordering verbatim for any OAuth redirect handler; adapt the baseline
resolution to your discovery cache; omit the fresh-discovery fallback only if your host always
persists `discoveryState` with codeVerifier-grade durability. Companion: auth.md (flow overview),
refresh-persistence-boundary.md (token persistence inside auth()).
