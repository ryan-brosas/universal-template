<!-- capsule-v2 -->
# Throttle classification ladder — when LinkedIn shows a block page, how do I classify WHICH limit hit and schedule the account pause?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** how do I turn ten different LinkedIn block screens into one typed decision (pause duration + scope), distinct from signal-based rate-limit detection?

## checkLimit — body-text probes → typed LinkedinErrors with a delay payload
**Path/Symbol:** `lib/linkedin/linkedin.abstract.service.ts:LinkedinAbstractService.checkLimit` (:162–243); consumer `checkToken` (:245–252); error enum `lib/enums/linkedin.errors.ts`.
**Signature:** `static async checkLimit(page: Page) -> void | throws LinkedinErrors(..., {values: LINKEDIN_ERRORS.DELAY, more: <minutes>}).
**Data Shape:** probe table rows = `{char, message, delay, type}` — `char` is the body-text needle, `message` the human diagnosis, `delay` minutes to postpone the account (`1440` daily limits, `120` hourly search/verification, `100000000` de-facto permanent restrictions), `type` scopes enforcement (`Connect` / `Page` / `All` / `restrictions`).

### Decisive source
```ts
const options = [
  { char: "You're reached the weekly invitation limit", message: "You're reached the weekly invitation limit", delay: 1440, type: "Connect" },
  { char: "Too Many Requests",                          message: "Too Many Search Requests",        delay: 120,  type: "Connect" },
  { char: "quick security check",                       message: "Verification Screen",             delay: 120,  type: "All" },
  { char: "we have restricted your account until",      message: "Account Restricted until some date", delay: 100000000, type: "restrictions" },
  // ...10 rows total; needles cover weekly invites, out-of-invitations,
  // no-Sales-Nav, search cap, security check, and three restriction phrasings
];
const isLimitedReached = (await page.evaluate((optionList) => {
  const body = document.querySelector("body")?.textContent?.trim();
  return optionList.map((option) => ({ ...option, char: body?.indexOf(option.char) }));
}, options)).filter((f) => f.char && f.char !== -1);
if (isLimitedReached.length) throw new LinkedinErrors(
  `We have postpone your activity, We got from Linkedin ${isLimitedReached[0].message}`,
  undefined, { values: LINKEDIN_ERRORS.DELAY, more: isLimitedReached[0].delay });
```

**Flow:** read body text ONCE in-page → map all probes over it (`indexOf`) inside the browser → filter hits (`char && char !== -1`, so index 0 still matches) → throw with the FIRST hit's message + delay + scope; the scheduler that catches `DELAY` parks the account for `more` minutes. Sibling `checkToken` (:245–252) is the session twin: fetch cookies for linkedin.com and throw `DISCONNECTED` iff cookie jar exists but `li_at` is gone.
**Invariant:** classification happens against ONE body-text snapshot evaluated in-page (no per-probe round trips); an empty jar is fine but a jar WITHOUT `li_at` means disconnected — never treat missing li_at as "just re-login" silently. The delay value travels on the ERROR — detection and scheduling must not be split across modules or the pause policy rots.
**Probe:** no upstream tests (stub only) — caveat recorded; boundary verified by reading abstract.service.ts at HEAD; graph anchor `checkLimit` resolves :162–243 exactly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "checkLimit invitation limit restricted DELAY", limit: 5 });
// resolves LinkedinAbstractService.checkLimit :162–243
```

## Verdict
Adopt the probe-table→typed-error-with-delay pattern and the li_at-presence session guard as the scheduler-facing complement to signal-based detection; adapt needle lists and delay values (they rot against live LinkedIn copy — re-verify before production); omit the hard-coded minute numbers as gospel. Contrast (see rate-limit-detection): joeyism detects via URL/CAPTCHA/body signals and raises immediately with retry discipline; linvo classifies the LIMIT KIND and lets an external scheduler decide when the account may act again — port both halves together for unattended fleets.
