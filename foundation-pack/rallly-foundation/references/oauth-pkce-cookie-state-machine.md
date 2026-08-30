<!-- capsule-v2 -->
# OAuth PKCE cookie state machine — how do you carry OAuth state across a cross-site redirect without a server-side session?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How does a stateless edge function survive the provider round-trip (state, PKCE verifier, post-connect destination) and still reject forged callbacks and open redirects?

## OAuthIntegration Hono factory with cookie-parked PKCE state
**Path/Symbol:** `apps/web/src/lib/oauth/server.ts:OAuthIntegration` (lines 17–167); redirect validator `apps/web/src/lib/utils/redirect.ts:validateRedirectUrl` (lines 13–36); consumer `apps/web/src/app/api/integrations/[...connection]/route.ts` (lines 24–75).
**Signature:** `OAuthIntegration<T extends string>({ basePath, getIntegration, cookieConfig? }) → { handler }`; `getIntegration({ integrationId, callbackUrl }) → OAuthClient | null`.
**Data Shape:** three httpOnly secure cookies under a configurable prefix (`oauth.` default), all sharing one TTL (`maxAge: 600` = 10 min default): `<prefix>state`, `<prefix>code-verifier`, `<prefix>redirect-to`. Failure output is always a redirect to the validated destination with an `error=` query param — never a rendered body.

### Decisive source
```ts
// auth endpoint parks all three values in cookies, not a session store
setCookie(c, STATE, state, { httpOnly: true, secure: ..., sameSite: ..., maxAge: cookieOptions.maxAge, path: "/" });
setCookie(c, CODE_VERIFIER, codeVerifier, { ... });
setCookie(c, REDIRECT_TO, redirectTo, { ... });   // redirectTo already validateRedirectUrl'd

// callback refuses to exchange unless BOTH hold
if (!code || !state || !storedState || state !== storedState || !codeVerifier) {
  const errorUrl = new URL(redirectTo, absoluteUrl());
  errorUrl.searchParams.set("error", "invalid_request");
  return c.redirect(errorUrl.toString());
}
const tokens = await integration.exchangeCode(code, codeVerifier);
```
```ts
// lib/utils/redirect.ts — leading-"/" alone is NOT enough
const PROBE_ORIGIN = "https://redirect-probe.invalid";
const trimmed = redirectTo.trim();
if (!trimmed.startsWith("/")) return undefined;
if (new URL(trimmed, PROBE_ORIGIN).origin !== PROBE_ORIGIN) return undefined;
```

**Flow:** GET `/auth/:id` → resolve integration (null ⇒ JSON error, no redirect) → generate state + codeVerifier (arctic) → validate-and-store redirect → set 3 cookies → redirect to provider. GET `/callback/:id` → re-resolve integration → read cookies → compare `state === storedState` AND require verifier presence → re-validate the stored redirect (second validation) → exchange code → fetch user info → run `onConnect` hook → redirect to destination with `connected=true&integration=<id>`. Any throw in the callback redirects with `error=connection_failed`.
**Invariant:** the callback trusts NOTHING from the query string except `code` and `state`, and even `state` only in comparison against the cookie. The redirect target is validated at BOTH write time and read time because the cookie value itself is the trust boundary. The sentinel-origin probe uses the WHATWG parser so `//evil.com`, `/\evil.com`, and tab/newline-stripped variants collapse exactly as the browser will collapse them. Cookie TTL bounds the whole flow: a stale half-finished connect dies after 10 minutes instead of lingering as a replayable state.
**Probe:** no upstream test for lib/oauth/server.ts or redirect.ts (caveat recorded). Behavioral anchors verified by direct read: cookie names at server.ts:31–33, `maxAge: 600` at :24, state comparison at :128, double `validateRedirectUrl` at :61 (write) and :121 (read), error redirects at :132/:159; PROBE_ORIGIN + origin comparison at redirect.ts:13/:26–28. Consumer confirmed: integrations route wires google-calendar with onConnect → saveOAuthCredentials → createCalendarConnection → syncCalendars.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "OAuthIntegration exchangeCode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the cookie-parked triple (state + PKCE verifier + validated redirect) for any stateless-edge OAuth dance, and adopt the sentinel-origin probe for every open-redirect gate — it is strictly stronger than a prefix check and costs one `new URL`. Adapt the Hono factory to your router; keep the `getIntegration → null` shape so unconfigured providers fail as JSON errors before any redirect. Omit the per-integration cookie prefix if you only ever run one integration. Caveat: no direct test suite pins this file; the redirect util is exercised indirectly by every login flow.
