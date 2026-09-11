<!-- capsule-v2 -->
# li_at-mint login — how do I turn a form login into a portable session token with exactly one failure mode?

**Source:** linvo-scraper ISC `main@cfbe91080c73`; Codebase Memory `linvo-scraper`. **Question:** what should a login service RETURN so every later browser/API plane can reuse the session, and how little error vocabulary does it need?

## LinkedinLoginService.process — type credentials, latch on search box, extract li_at
**Path/Symbol:** `lib/linkedin/linkedin.login.service.ts:LinkedinLoginService.process` (:18–56).
**Signature:** `process(page, cdp, data: { user: string; password: string }) -> Promise<{ user: string; token: string }>`.
**Data Shape:** success payload carries the username plus ONLY the `li_at` cookie value minted by this login; ANY failure (bad selector, timeout, checkpoint) becomes ONE typed error.

### Decisive source
```ts
await (await page.$("#username"))?.type(data.user, { delay: 30 });
await timer(500);
await (await page.$("#password"))?.type(data.password, { delay: 30 });
await timer(1000);
await (await page.$("button[type=submit]"))?.click();
await timer(3000);
await page.waitForSelector(".search-global-typeahead__input", { timeout: 30000 });
const token = await page.cookies();
return {
  user: data.user,
  token: token?.find((t) => t.name === "li_at")?.value,
};
} catch (err) {
throw new LinkedinErrors(
  "Could not login to linkedin, please update you credentials",
  '/accounts',
  { values: LINKEDIN_ERRORS.INVALID_CREDENTIALS }
);
```

**Flow:** goto /login → wait #username → timer(4000) → type user at 30 ms/char → timer(500) → type password at 30 ms/char → timer(1000) → click submit → timer(3000) → SUCCESS LATCH = global search typeahead visible within 30 s → read all cookies → project to `{user, token: li_at}`. Anything else ⇒ `LinkedinErrors(msg, '/accounts', INVALID_CREDENTIALS)` — the route field tells the scheduler where to send the user next.
**Invariant:** login is a TOKEN MINTING step, not a destination — it returns a value a DIFFERENT session can plant (`setCookie li_at`, see cookie-session-bootstrap) or an API client can header-encode (see dual-persona-auth-headers); success is declared by a POST-login UI latch, never by absence of error; the failure vocabulary is exactly ONE value (INVALID_CREDENTIALS) because every login failure has the same remediation.
**Probe:** no upstream tests (blocker). Deterministic anchor: `li_at` find + INVALID_CREDENTIALS throw shape at HEAD — verification.md probe P5.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "login li_at INVALID_CREDENTIALS", limit: 5 });
```
Resolves `LinkedinLoginService.process` :18–56 rank 1.

## Verdict
Adopt return-the-token (decouple authentication from browsing), the positive success latch, and the single-valued failure enum with scheduler route. Adapt typing delays/jitter to your humanization budget. Omit nothing structural; do NOT widen the catch into per-error classes — checkpoint/challenge pages belong to the throttle classifier, not the credential check.
