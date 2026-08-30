<!-- capsule-v2 -->
# Two-step 2FA with partial-auth tokens — how do you split login across a password step and an OTP step safely?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How is the between-steps credential scoped so it can only ever complete ITS OWN login?

## partial-auth-2fa
**Path/Symbol:** `src/app/api/auth/login/route.ts:33-42` (partial mint); `src/app/api/2fa/verify/route.ts:POST` (redemption ladder :19-146).
**Signature:** step 1 → `createSecureToken({ userId, type: 'partial-auth' }, secret(), { expiresIn: '5m' })`; step 2 requires `payload.type === 'partial-auth'` then issues the full session token.
**Data Shape:** body union `z.union([{token: length(6)}, {backupCode}]).strict()`; response of step 1 `{ requiresTwoFactor: true, partialToken }`.

### Decisive source
```ts
const payload = parseSecureToken(rawToken, secret()) as any;
if (!payload || payload.type !== 'partial-auth' || !payload.userId) {
  return unauthorized({ code: 'two-factor-error-invalid-partial-token' });
}
...
if (!twoFactor?.isEnabled) {           // 2FA disabled AFTER a partial token was issued
  return badRequest({ code: 'two-factor-error-not-enabled', ... });
}
```

**Flow:** password OK + 2FA on → 5-minute `partial-auth` token (NOT a session); `/api/2fa/verify` re-proves possession (TOTP or backup code) → rate-limit check → consume OTP/mark code used → mint full token. Cloud mode returns `notFound()` for the whole endpoint.
**Invariant:** the type discriminator keeps a FULL auth token from being replayed into the verify route (and the partial token can't be replayed into normal routes because nothing accepts `type:'partial-auth'` except this handler). A user disabling 2FA mid-flow must NOT get a free login — hence the explicit not-enabled rejection instead of auto-completing.
**Probe:** `grep -c "^test(" src/app/api/2fa/verify/route.test.ts` → 2 (direct test ships); error-code strings pin behavior: `grep -c "two-factor-error-" src/app/api/2fa/verify/route.ts` → ≥7 lines.
**Probe:** `grep -n "partial-auth" src/app/api/auth/login/route.ts src/app/api/2fa/verify/route.ts` → one line each.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "partialToken requiresTwoFactor partial auth", limit: 10 });
```

## Verdict
Adopt typed short-TTL intermediate credentials for any multi-factor/multi-step handshake; adapt TTL (5m) and error-code vocabulary; omit cloud-mode gating.
