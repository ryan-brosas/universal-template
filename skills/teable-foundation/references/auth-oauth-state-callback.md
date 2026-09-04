<!-- capsule-v2 -->
# OAuth state + callback guard — how do you make social sign-in state single-use and the post-login redirect un-hijackable?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How should OAuth2 `state` be stored/verified and how must the callback validate a user-supplied redirect target?

## Consume-once state store + path-only redirect validation
**Path/Symbol:** `apps/nestjs-backend/src/features/auth/oauth/oauth.store.ts` : `store` (:14–27), `verify` (:29–41); `apps/nestjs-backend/src/features/auth/social/controller.adapter.ts` : `isValidRedirectPath` (:4–12), `ControllerAdapter.callback` (:18–29).
**Signature:** `store(req, callback, ...args)` / `verify(req, stateId, callback)` (passport-oauth2 `OAuth2.CustomStore` shape); `callback(req, res, defaultRedirectUri?): Promise<void>`.
**Data Shape:** Cache key `oauth2:{random16}` → `{redirectUri: req.query.redirect_uri}` with 12h TTL; authInfo carries `{state: IOauth2State}` back to the adapter.

### Decisive source
```ts
async verify(_req, stateId, callback) {
  const state = await this.cacheService.get(`oauth2:${stateId}`);
  if (state) {
    await this.cacheService.del(`oauth2:${stateId}`);   // consume-once: replay dies here
    callback(null, true, state);
  } else { callback(null, false, 'Invalid authorization request state'); }
}
```
```ts
function isValidRedirectPath(path: string): boolean {
  try {
    const base = 'http://placeholder.local';
    const url = new URL(path, base);
    return url.origin === base && (url.protocol === 'http:' || url.protocol === 'https:');
  } catch { return false; }
}
// callback: req.login(user) → redirect(state.redirectUri if valid) || defaultRedirectUri || '/'
```

**Flow:** Authorization request mints a 16-char random state id, parks `{redirectUri}` under `oauth2:{id}` for 12h, and hands the id to passport. Callback verifies by reading AND deleting in one breath — a second redemption of the same state finds nothing. After `req.login` establishes the session, the redirect target from state is accepted only if it parses as a RELATIVE path against a placeholder origin (any absolute or protocol-relative URL changes `url.origin` and is rejected); otherwise the default redirect or `/`.
**Invariant:** State verification is destructive-read; redirect validation is origin-equality against a synthetic base, which admits only same-site paths and rejects open-redirect payloads (`//evil.com`, `https://evil.com`) — not just string-prefix checks.
**Probe:** No dedicated upstream spec (coverage caveat). Deterministic probe executed this pass: byte-check of both files at HEAD; behavioral reasoning pinned above (`new URL('//evil.com','http://placeholder.local').origin !== base` ⇒ rejected) recorded as source-visible semantics with no direct test.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "teable", label: "Class", name_pattern: "^(OauthStoreService|ControllerAdapter)$" })
→ OauthStoreService @ .../auth/oauth/oauth.store.ts lines 9-42; ControllerAdapter @ .../auth/social/controller.adapter.ts lines 14-30 (executed live this pass)
```

## Verdict
Adopt: cache-backed consume-once state with TTL, and placeholder-origin URL parsing as the redirect allowlist. Adapt key prefix/TTL and provider strategy wiring. Omit github/google/oidc controller specifics — they all delegate to this adapter.
