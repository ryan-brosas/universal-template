<!-- capsule-v2 -->
# Session verification carry-over — when does a fresh login inherit trusted-device status?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** After `req.session.regenerate()` on login, which session fields survive and under what binding?

## createSessionForUser + isVerifiedSession
**Path/Symbol:** `ghost/core/core/server/services/auth/session/session-service.js:createSessionForUser` (:206–248; carry logic :229–237) and `isVerifiedSession` (:487–497).
**Signature:** `async createSessionForUser(req, res, user)`; `async isVerifiedSession(req, res): Promise<boolean>`.
**Data Shape:** session fields: user_id, origin, user_agent, ip, verified (bool|undefined), verified_user_id, auth_code_challenge, auth_code_generated_at.
### Decisive source
```js
session.user_id = previousUserId;
// Verification is bound to the user who completed it — any other user
// (including sessions with no verified_user_id) must verify again
const carryVerification = previousVerified === true && previousVerifiedUserId === user.id;
session.verified = carryVerification ? true : undefined;
session.verified_user_id = carryVerification ? previousVerifiedUserId : undefined;
...
return (
  session.verified === true &&
  !!session.verified_user_id &&
  session.verified_user_id === session.user_id
);
```
**Flow:** capture 5 fields from the OLD session → `regenerate` (new session id — fixation defense) → restore user_id always; verified/verified_user_id ONLY if the completed verification belonged to THIS user → assignUserToSession stamps origin/UA/ip and honors a verification token if present.
**Invariant:** Verification is a (session, user) PAIR: same user re-login keeps device trust across regeneration; different user (or legacy session with verified=true but no verified_user_id) fails closed because `!!verified_user_id` rejects undefined===undefined matches. Logout (`removeUserForSession` :506–516) clears verified fields ONLY when email MFA is required — device trust intentionally survives logout otherwise.
**Probe:** `grep -cF "carryVerification = previousVerified === true && previousVerifiedUserId === user.id" ghost/core/core/server/services/auth/session/session-service.js` → expect `1`; `grep -cF "!!session.verified_user_id &&" ghost/core/core/server/services/auth/session/session-service.js` → expect `1`; direct tests pin all three cases: `grep -cF "it('#createSessionForUser does not carry verification over to a different user'" ghost/core/test/unit/server/services/auth/session/session-service.test.js` → `1`; `grep -cF "it('#createSessionForUser keeps trusted-device verification for the same user after logout'" ...same file` → `1`; `grep -cF "it('Treats legacy verified sessions without verified_user_id as unverified'" → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "createSessionForUser", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pair-bound verification carry-over with fail-closed legacy handling. Adapt the express-session regenerate call; keep regenerate-before-assign ordering (fixation).
