<!-- capsule-v2 -->
# Email MFA challenge lifecycle — how does the 6-digit email code bind to a session?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What prevents a code emailed for one session (or one user) from verifying another, and when is it required vs device-triggered?

## Auth-code challenge + middleware decision
**Path/Symbol:** `ghost/core/core/server/services/auth/session/session-service.js:rotateAuthCodeChallenge` (:81–104) and `verifyAuthCode` (:106–118); decision in `ghost/core/core/server/services/auth/session/middleware.js:createSession` (:4–30).
**Signature:** `rotate(session)`; `verifyAuthCode(session, token, secret): boolean`; constants `AUTH_CODE_VALIDITY_MS = 5*60*1000`, `AUTH_CODE_CHALLENGE_BYTES = 16`.
**Data Shape:** session.auth_code_challenge = 32-hex random; session.auth_code_generated_at = ms epoch. TOTP secret = `admin_session_secret` setting; code delivered by email with device details (UA parse + geojs IP lookup, 500ms timeout, fail-open 'Unknown').
### Decisive source
```js
function verifyAuthCode(session, token, secret) {
  if (!token || !session.user_id || !hasValidAuthCodeChallenge(session)) { return false; }
  const verified = totp.verify(session.user_id, token, secret, session.auth_code_challenge);
  if (verified) { invalidateAuthCodeChallenge(session); }   // single-use
  return verified;
}
```
middleware.js:
```js
throw new errors.NoPermissionError({
  code: sessionService.isVerificationRequired() ? '2FA_TOKEN_REQUIRED' : '2FA_NEW_DEVICE_DETECTED',
  ...
  errorType: 'Needs2FAError',
});
```
**Flow:** login creates unverified session → middleware sees not-verified → rotates challenge, emails code → responds Needs2FAError with code distinguishing policy-MFA (`require_email_mfa` setting true) from new-device verification (flag-disabled path auto-verifies). Client POSTs code → verifyAuthCodeForUser runs cookieCsrfProtection first → TOTP verified against session's OWN challenge → challenge invalidated.
**Invariant:** The challenge lives ON the session and regenerates per send — a code cannot be replayed across sessions or after one success. `createSessionForUser` invalidates the carried-over challenge whenever the session switches users (:171–173). Verification survives only as the (verified, verified_user_id) pair — see carry-over capsule.
**Probe:** `grep -cF "AUTH_CODE_VALIDITY_MS = 5 * 60 * 1000" ghost/core/core/server/services/auth/session/session-service.js` → expect `1`; `grep -cF "2FA_NEW_DEVICE_DETECTED" ghost/core/core/server/services/auth/session/middleware.js` → expect `1`; direct test: `grep -cF "it('#createSessionForUser does not verify session when token belongs to a different session challenge'" ghost/core/test/unit/server/services/auth/session/session-service.test.js` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "cookieCsrfProtection origin admin", limit: 10, fields: ["signature", "name", "file"] });
```
**Drift note:** BM25 ranks session-service functions under origin/CSRF queries; query `isVerifiedSession verified_user_id` resolves this file rank-1.

## Verdict
Adopt per-session rotating TOTP challenge with single-use invalidation and the two-reason Needs2FA split. Adapt delivery channel; keep geo/UA enrichment fail-open ('Unknown') so mail never blocks on lookup failure.
