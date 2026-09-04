<!-- capsule-v2 -->
# SEP-2350 step-up authorization — how does a client widen OAuth scope mid-session without losing grants or retrying forever?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** On a 403 insufficient_scope challenge, what exact scope does the re-authorization request carry, when must refresh be bypassed, and what bounds the loop?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/streamableHttp.ts`: `_stepUpAuthorize` (:374-383, method-level auth-seam stamp) wrapping `_stepUpAuthorizeInner` (:385-433); consumed by both `_send` (:1056-1069) and `_startOrAuthSse` (:592-605).
**Signature:** `private async _stepUpAuthorize(challenge: StepUpChallenge, stepUpRetries: number): Promise<'AUTHORIZED' | 'REDIRECT'>`
**Data Shape:** challenge = parsed WWW-Authenticate of the 403 (`error="insufficient_scope"`, scope, resource_metadata_url, error_description); transport tracks \`_scope\` and \`_resourceMetadataUrl\` across attempts.

### Decisive source
```ts
// :402-408 — bounded per send; :414-429 — union + superset-gated refresh bypass
if (stepUpRetries >= this._maxStepUpRetries) {
    throw new SdkHttpError(SdkErrorCode.ClientHttpForbidden,
      `Server returned 403 insufficient_scope after step-up re-authorization (retry limit ${this._maxStepUpRetries} reached)`,
      { status: 403, statusText: challenge.statusText ?? 'Forbidden', text: challenge.text });
}
const tokens = await this._oauthProvider.tokens();
const unionScope = computeScopeUnion(this._scope, tokens?.scope, challenge.scope);
this._scope = unionScope; // never narrows: a later 401 merges, not replaces
const forceReauthorization = isStrictScopeSuperset(unionScope, tokens?.scope);
return auth(this._oauthProvider, { serverUrl: this._url, scope: unionScope,
    forceReauthorization, fetchFn: this._fetchWithInit, ... });
```

**Flow:** 403 with insufficient_scope → 'throw' mode or missing OAuth provider short-circuits to
typed InsufficientScopeError → else if retry budget remains, compute union(transport-tracked,
token-granted, challenged), persist it on the transport → force a FRESH authorization request iff
the union strictly exceeds granted scope (RFC 6749 §6: refresh cannot widen) → retry the original
send/stream-open with stepUpRetries+1 → exhausted budget throws SdkHttpError(ClientHttpForbidden).

**Invariant:** previously-granted permissions are never dropped (union, not replace); the retry
counter is per-send-chain, not transport-wide — cross-request "this operation keeps failing"
tracking is host responsibility; every escape from the OAuth flow is marked as an auth-seam
escape so bundle-duplicated brand checks still classify it.

**Probe:** `packages/client/test/client/streamableHttp.test.ts` :1071-1113 (default cap 1:
exactly 2 fetches + 1 auth() call per send; second send retries once again — fresh counter) and
:1115+ (challenge "b c" then "d" against token scope "a b" unions upward across attempts).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typescript-sdk", query: "step-up insufficient_scope computeScopeUnion isStrictScopeSuperset", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt union-scope re-authorization with the superset-gated refresh bypass and a per-exchange
bounded counter; adapt where the consent UX gates 'reauthorize' vs 'throw'; omit interactive
redirects for m2m hosts. Snippet verified via get_code_snippet (:385-433) at the pin.
