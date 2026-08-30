<!-- capsule-v2 -->
# Password-fingerprint token invalidation — how do JWTs die the moment a password changes, without a denylist?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How does stateless auth invalidate old tokens on password change with no server-side session store?

## pwd-fingerprint-auth
**Path/Symbol:** `src/app/api/auth/login/route.ts:44-56` (mint); `src/lib/auth.ts:checkAuth :23-84` (verify); direct tests `src/lib/auth.test.ts:59-119`.
**Signature:** login mints `createSecureToken({ userId, role, pwd: hash(user.password) }, secret())`; verify re-derives `hash(user.password)` and compares.
**Data Shape:** `pwd` = sha512 of the bcrypt hash string (NOT the password). Redis mode stores the payload under `auth:<random>` and signs only `{ authKey }`.

### Decisive source
```ts
// auth.ts — verification side
if (user && payload.pwd && hash(user.password) !== payload.pwd) {
  user = null;                       // token predates current password ⇒ dead
}
...
// Legacy tokens minted WITHOUT a fingerprint stay valid (migration escape hatch):
// "Allow legacy stateless tokens that were minted without a password fingerprint."
if (user && key.pwd && hash(user.password) !== key.pwd) { user = null; }   // redis branch
```

**Flow:** password change → stored bcrypt hash changes → every outstanding token's `pwd` no longer matches → rejected at next request. No revocation list, no jti tracking.
**Invariant:** ABSENCE of `pwd` must NOT reject (`payload.pwd &&` guard) — that's the documented legacy-token allowance; a porter who flips it to require `pwd` breaks upgrades. The user object is stripped of `password` before returning (`delete user.password`) — never leak the hash through auth context.
**Probe:** `grep -cn "fingerprint predates a password change" src/lib/auth.test.ts` → 1 (:78) with `:69` legacy-token acceptance pinning both branches.
**Probe:** `grep -n "legacy stateless token" src/lib/auth.test.ts` → :69.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "checkAuth saveAuth pwd fingerprint", limit: 10 });
```

## Verdict
Adopt fingerprint-carrying tokens as the cheapest password-change invalidation for stateless APIs; adapt to include other mutable claims (email verified, role bump); omit Redis session branch if you have no cache tier.
