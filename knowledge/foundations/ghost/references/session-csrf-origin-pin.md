<!-- capsule-v2 -->
# Session CSRF origin pin — how are cookie-authenticated admin requests bound to the admin origin?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What stops a cross-origin no-cors form from replaying an admin session cookie, and where is the bypass hatch?

## cookieCsrfProtection
**Path/Symbol:** `ghost/core/core/server/services/auth/session/session-service.js:cookieCsrfProtection` (:127–152); enforcement points `verifyAuthCodeForUser` (:332–340), `sendAuthCodeToUser` (:411–466), `getUserForSession` (:525–548).
**Signature:** `(req, session): void` (throws).
**Data Shape:** request origin via injected `getOriginOfRequest(req)`; expected = `urlUtils.getAdminUrl() || urlUtils.getSiteUrl()`.
### Decisive source
```js
const origin = getOriginOfRequest(req);
const adminUrl = urlUtils.getAdminUrl() || urlUtils.getSiteUrl();
const adminOrigin = new URL(adminUrl).origin;
if (origin !== adminOrigin) { throw new BadRequestError({...}); }
// If there is no origin on the session object it means this is a *new*
// session, that hasn't been initialised yet.
if (!session.origin) { return; }
if (session.origin !== origin) { throw new BadRequestError({...}); }
```
**Flow:** every session-consuming call runs: request origin must equal ADMIN origin (first line of defense even for brand-new sessions) → then session's pinned origin must equal request origin (binds the whole session lifetime to the first login origin). `getUserForSession` skips the check only when `res.locals.bypassCsrfProtection` was set upstream (OAuth flows).
**Invariant:** Two-layer check: config-level (admin origin) applies ALWAYS — a stolen cookie from another site fails even before session binding. Session-origin pinning survives because assignUserToSession stamps `session.origin` at creation (:176). Exact string equality after `new URL(...).origin` normalization — no suffix matching.
**Probe:** `grep -cF "new URL(adminUrl).origin" ghost/core/core/server/services/auth/session/session-service.js` → expect `1`; `grep -cF "session.origin !== origin" ghost/core/core/server/services/auth/session/session-service.js` → expect `1`; direct tests: `grep -cF "it('Throws an error when the csrf verification fails due to non-admin origin'" ghost/core/test/unit/server/services/auth/session/session-service.test.js` and `"Doesn't throw an error when the csrf verification fails when bypassed"` both → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "cookieCsrfProtection origin admin", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-layer origin equality with explicit bypass flag for SSO handoffs. Adapt origin extraction to host headers; never downgrade to Referer-only.
