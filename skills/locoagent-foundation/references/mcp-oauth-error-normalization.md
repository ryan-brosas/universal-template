<!-- capsule-v2 -->
# OAuth error-body normalization — how do I make always-200 OAuth servers (Slack) surface invalid_grant to the SDK's error mapping?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Why does a 200-with-error-body break token-refresh classification, and what is the minimal fetch-wrapper fix?

## 2xx peek → schema-match rewrite → alias normalization → 400 reconstruction
**Path/Symbol:** `src/services/mcp/auth.ts`: `normalizeOAuthErrorBody` (:157-190), `NONSTANDARD_INVALID_GRANT_ALIASES` (:147-151), applied POST-only inside `createAuthFetch` (:201,:207,:231).
**Signature:** `normalizeOAuthErrorBody(response: Response): Promise<Response>`; aliases {invalid_refresh_token, expired_refresh_token, token_expired} → `invalid_grant`.
**Data Shape:** Rewrite condition: parsed body matches `OAuthErrorResponseSchema` AND NOT `OAuthTokensSchema`; success bodies pass through untouched (DCR responses have no `{error:string}` field so they never match :133-140 comment).

### Decisive source
```ts
// Some OAuth servers (notably Slack) return HTTP 200 for all responses,
// signaling errors via the JSON body instead. The SDK's executeTokenRequest
// only calls parseErrorResponse when !response.ok, so a 200 with
// {"error":"invalid_grant"} gets fed to OAuthTokensSchema.parse() and
// surfaces as a ZodError — which the refresh retry/invalidation logic
// treats as opaque request_failed instead of invalid_grant.
//
// This wrapper peeks at 2xx POST response bodies and rewrites ones that
// match OAuthErrorResponseSchema ... to a 400 Response, so the SDK's normal
// error-class mapping applies.
const normalized = NONSTANDARD_INVALID_GRANT_ALIASES.has(result.data.error)
  ? { error: 'invalid_grant',
      error_description: result.data.error_description ??
        `Server returned non-standard error code: ${result.data.error}` }
  : result.data
return new Response(jsonStringify(normalized), {
  status: 400, statusText: 'Bad Request', headers: response.headers,
})
```

**Flow:** POST token/refresh request → createAuthFetch applies normalizeOAuthErrorBody on POST responses ONLY (GETs pass through) → Slack-style 200+error becomes a real 400 → SDK maps to InvalidGrantError → refreshAuthorization's invalid-grant arm runs its cross-process storage recheck and invalidates correctly; non-JSON 200 bodies are returned as-is (captive portals).
**Invariant:** The OAuthTokensSchema exclusion must run BEFORE the error-schema test or valid token responses would be rewritten; normalization applies only to POSTs (metadata discovery GETs must not be touched).
**Probe:** `grep -nF "'invalid_refresh_token'," src/services/mcp/auth.ts | head -1` (`148:`) and `grep -c 'isPost ? normalizeOAuthErrorBody(response) : response' src/services/mcp/auth.ts` (`2` — both the no-signal and combined-signal branches of createAuthFetch).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "normalizeOAuthErrorBody", limit: 5 });
```

## Verdict
Adopt the peek-and-rewrite wrapper with alias table and POST-only application. Adapt the alias set as you observe more non-standard IdPs. Omit vendor commentary beyond provenance.
