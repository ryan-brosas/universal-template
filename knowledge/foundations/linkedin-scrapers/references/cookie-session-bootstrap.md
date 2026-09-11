<!-- capsule-v2 -->
# Cookie-session bootstrap — how do I authenticate a browser scraper without ever scripting the login?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** How do I get a logged-in session into an automation browser without tripping login-request blocks — and how do I know the session died?

## Plant cookie, then redirect-probe
**Path/Symbol:** `src/index.ts:LinkedInProfileScraper.createPage` (:352–360) + `checkIfLoggedIn` (:465–493); option contract `ScraperUserDefinedOptions.sessionCookieValue` (:97–109); typed error `src/errors.ts:SessionExpired`.
**Signature:** `page.setCookie({ name: 'li_at', value: options.sessionCookieValue, domain: '.www.linkedin.com' })` → `checkIfLoggedIn(): Promise<void>` (throws `SessionExpired`).
**Data Shape:** ONE string option — the raw `li_at` cookie value hand-extracted from a real logged-in browser. No email/password exists anywhere in the process.

### Decisive source
```ts
await page.setCookie({
  'name': 'li_at',
  'value': this.options.sessionCookieValue,
  'domain': '.www.linkedin.com'
})
...
// Go to the login page. If we do not get redirected and stay on /login,
// we are logged out. If we get redirected to /feed, we are logged in.
await page.goto('https://www.linkedin.com/login', { waitUntil: 'networkidle2', timeout: this.options.timeout })
const url = page.url()
const isLoggedIn = !url.endsWith('/login')
```

**Flow:** user extracts `li_at` once from their own browser → constructor rejects empty/non-string values before any launch (:180–186) → EVERY created page plants the cookie before navigation → probe navigates to `/login`: redirect away = alive, still on `/login` = dead → typed `SessionExpired` error whose message tells the user to re-extract the cookie.
**Invariant:** never automate the credential login itself — the option's doc comment records WHY: LinkedIn blocks or CAPTCHAs login requests from unknown locations, which kills server-hosted scrapers; the cookie IS the auth. Expiry is surfaced LOUDLY as a distinct error, never silently retried. `checkIfLoggedIn` runs inside `setup()` immediately after launch (:273), so a dead cookie fails fast at startup instead of mid-scrape.
**Probe:** `src/index.test.ts` pins the option validation (`'Error during setup. Option "sessionCookieValue" is required.'` / `needs to be a string.`); the redirect semantics themselves are live-site behavior — source-grounded only, re-verify before production.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "checkIfLoggedIn SessionExpired setCookie", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt cookie-first auth + the `/login` redirect probe + the typed expired-session error for ANY automation against a login-walled site (this is the minimal single-cookie sibling of the suite's `sessions-json-cache` and `cookie-session-persistence`). Adapt cookie name/domain per target. Omit credential-flow automation entirely. Caveat: no automated test drives a live browser; the redirect outcome is environment-dependent.
