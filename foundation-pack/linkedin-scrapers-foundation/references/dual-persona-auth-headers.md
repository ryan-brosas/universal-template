<!-- capsule-v2 -->
# Dual-persona auth — mobile-app headers to authenticate, browser headers to call the API (why does my private-API login work but every API call 999s?)

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** Which header personas must a cookie-based LinkedIn API client present, and how do the login endpoint and the voyager endpoints differ?

## Two header sets, one session
**Path/Symbol:** `config/index.ts:authHeaders` + `requestHeaders`; `src/core/login.ts:setRequestHeaders` (:28–36); `src/requests/auth.request.ts:authenticateUser` (:18–37).
**Signature:** `setRequestHeaders({ cookies }: { cookies: AuthCookies }): void` — mutates `client.request.setHeaders(...)` (axios `defaults.headers`).
**Data Shape:** `authHeaders` = iOS app persona (`user-agent: LinkedIn/8.8.1 CFNetwork/711.3.18 Darwin/14.0.0`, `X-Li-User-Agent: LIAuthLibrary:3.2.4 com.linkedin.LinkedIn:8.8.1 iPhone:8.3`, `Content-Type: application/x-www-form-urlencoded`, hardcoded `'Content-Length': '110'` that never varies with credentials — vestigial under axios (which recomputes per request) but a porting TRAP if copied verbatim into clients that honor caller-supplied lengths); `requestHeaders` = desktop web persona (`authority`, `x-restli-protocol-version: 2.0.0`, `x-li-lang`, `x-li-page-instance: urn:li:page:d_flagship3_feed;...`, `accept: application/vnd.linkedin.normalized+json+2.1`, `x-li-track` clientVersion JSON, sec-fetch pair, feed referer).

### Decisive source
```ts
private setRequestHeaders({ cookies }: { cookies: AuthCookies }): void {
  const cookieStr = reduce(cookies, (res, v, k) => `${res}${k}="${v}"; `, '');
  this.client.request.setHeaders({
    ...requestHeaders,
    cookie: cookieStr,
    'csrf-token': cookies.JSESSIONID!,
  });
}
// auth POST (AuthRequest.authenticateUser): queryStringify({ session_key, session_password, JSESSIONID }) with authHeaders
```

**Flow:** GET `https://www.linkedin.com/uas/authenticate` with app persona → harvest anonymous `JSESSIONID` from `set-cookie` → POST same URL, form-encoded creds + that sessionId, still app persona → response `set-cookie` carries the authenticated jar (`JSESSIONID` + `authenticated=true`) → switch the shared axios instance to the BROWSER persona for all subsequent `/voyager/api` calls, with CSRF `csrf-token` = the raw JSESSIONID value and cookies serialized as `k="v"; ` pairs.
**Invariant:** the two personas are NOT interchangeable — the auth endpoint expects the mobile-app fingerprint while `/voyager/api` enforces restli protocol + normalized-JSON accept + csrf-from-JSESSIONID; sending browser headers to authenticate or app headers to fetch fails. The CSRF token is the FULL session id verbatim (contrast suites that strip the `ajax:` prefix — see voyager-api-client capsule; this repo keeps it). Cookie values are wrapped in literal double quotes in the header.
**Probe:** `test/login/login.spec.ts:29–41` pins the exact merged header object after userPass (`cookie: 'JSESSIONID="ajax:445..."; authenticated="true"; '`, `'csrf-token': sessionId`); :57–82 pins zero axios calls when cache hits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "setRequestHeaders authHeaders", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the persona split (app identity for credential exchange, web identity for API surface) and csrf-token=JSESSIONID wiring — it generalizes to any vendor that fronts one API with several client fingerprints. Adapt UA versions/page-instance urns (they age). Runner-up in-suite: open-linkedin-api's android-header split (voyager-password-auth-metadata) — same idea, different persona; this repo adds the explicit two-config separation. Direct tests pin the exact header merge.
