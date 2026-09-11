<!-- capsule-v2 -->
# Authorization two-phase error split — which authorize failures answer directly with 400 and which must ride the redirect back to the client?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When porting the `/authorize` endpoint, exactly where does the pre-redirect/post-redirect error boundary sit, and why?

## Two-phase handler & RFC 8252 loopback relaxation
**Path/Symbol:** `packages/server-legacy/src/auth/handlers/authorize.ts`: `redirectUriMatches` (:41-60), schemas (:63-79), `authorizationHandler` (:81-200), `withIssOnCallbackRedirect` (:210-233), `createErrorRedirect` (:238-253).
**Signature:** `redirectUriMatches(requested: string, registered: string): boolean`; handler `router.all('/', …)` accepting GET and POST form bodies.
**Data Shape:** Phase 1 validates only `{client_id, redirect_uri?}` (`ClientAuthorizationParamsSchema`) — the minimum needed to know WHERE a redirect could go; Phase 2 validates `{response_type:'code', code_challenge, code_challenge_method:'S256', scope?, state?, resource?}`.

### Decisive source
```ts
// :105-109 the contract in four comment lines
// In the authorization flow, errors are split into two categories:
// 1. Pre-redirect errors (direct response with 400)
// 2. Post-redirect errors (redirect with error parameters)
```
```ts
// :52-59 port relaxation is loopback-host PAIRED and exact on everything else
if (!LOOPBACK_HOSTS.has(req.hostname) || !LOOPBACK_HOSTS.has(reg.hostname)) {
    return false;   // LOOPBACK_HOSTS = {'localhost','127.0.0.1','[::1]'} — no cross-matching
}
return req.protocol === reg.protocol && req.hostname === reg.hostname && req.pathname === reg.pathname && req.search === reg.search;
```

**Flow:** Phase 1 (try/catch #1): schema parse → `getClient` → redirect_uri registered check (or default to the single registered URI; error when multiple and none given) — any throw answers `res.status(400|500).json(error.toResponseObject())` DIRECTLY because no safe redirect target exists yet. Phase 2 (try/catch #2): full param validation → `provider.authorize(client, params, wrappedRes)` — any OAuthError here becomes `res.redirect(302, createErrorRedirect(redirect_uri, error, state, iss))`, carrying `error`, `error_description`, optional `error_uri`, `state`, and RFC 9207 `iss`. Rate limit 100/15min rides before both phases unless `rateLimit:false`.

**Invariant:** the boundary is "can I safely redirect there yet?" — validating response_type or code_challenge BEFORE knowing client+redirect_uri risks leaking validation state to an attacker-controlled URL; conversely answering a Phase 2 failure directly strands the browser on the AS origin. Loopback port relaxation applies ONLY when BOTH URIs are loopback AND same host spelling, scheme, path, query — relaxing path or scheme would let native-app phishers ride ephemeral ports onto other paths.

**Probe (direct tests):** `packages/server-legacy/test/auth/handlers/authorize.test.ts` — describe 'redirectUriMatches (RFC 8252 §7.3)' :241-281 pins nine cases incl. 'loopback: localhost↔127.0.0.1 cross-match rejected' :264 and 'non-loopback: no relaxation for private IPs' :273; :136 'uses the only redirect_uri if client has just one and none provided'; RFC 9207 block :401+ ('appends iss to error redirects' :451).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "redirectUriMatches loopback port relaxation", limit: 3 });
// → packages/server-legacy/src/auth/handlers/authorize.ts redirectUriMatches Function 41-60 rank #1
```

## Verdict
Adopt the two-phase split and paired-loopback port relaxation verbatim — they encode RFC 6749/8252/9207 obligations; adapt storage of challenges/codes behind your provider interface; omit express-rate-limit defaults if your edge already limits.
