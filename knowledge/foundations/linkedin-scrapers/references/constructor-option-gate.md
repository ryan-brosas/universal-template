<!-- capsule-v2 -->
# Constructor option gate — where do invalid scraper options die, and how do defaults survive them?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** How do I validate user-supplied options BEFORE they can overwrite safe defaults — and keep the error messages byte-for-byte testable?

## Validate-before-merge onto readonly defaults
**Path/Symbol:** `src/index.ts:LinkedInProfileScraper.constructor` (:176–207); contracts `ScraperUserDefinedOptions` (:97–136) and resolved `ScraperOptions` (:138–144).
**Signature:** `constructor(userDefinedOptions: ScraperUserDefinedOptions)` — synchronous plain-`Error` throws sharing the constant prefix `errorPrefix = 'Error during setup.'` (:178).
**Data Shape:** a class-field object holds the FULL defaults (`sessionCookieValue: ''`, `keepAlive: false`, `timeout: 10000`, Chrome-69 UA string, `headless: true`); optional fields use the pattern `X !== undefined && typeof X !== T` so ABSENT passes and WRONG-TYPED throws; the required `sessionCookieValue` also rejects falsy values.

### Decisive source
```ts
const errorPrefix = 'Error during setup.';
if (!userDefinedOptions.sessionCookieValue) {
  throw new Error(`${errorPrefix} Option "sessionCookieValue" is required.`);
}
if (userDefinedOptions.timeout !== undefined && typeof userDefinedOptions.timeout !== 'number') {
  throw new Error(`${errorPrefix} Option "timeout" needs to be a number.`);
}
...
this.options = Object.assign(this.options, userDefinedOptions);
```

**Flow:** presence gate on the required credential → typeof ladder across each PROVIDED optional (per-field boolean/number/string) → merge onto untouched defaults → log the resolved options. Merge happens LAST, so a rejected value can never partially clobber configuration; the constant prefix makes whole messages part of the tested API surface.
**Invariant:** validation PRECEDES assignment, and error text is stable — six byte-exact messages are asserted directly by the test suite. Absence ≠ invalid: unset optionals fall through to defaults rather than failing.
**Probe:** `src/index.test.ts` — constructor-only suite (defaults spread, per-field overrides, wrong-type rejections for headless/keepAlive/sessionCookieValue/timeout/userAgent); runs WITHOUT browser or network (executed green this pass via staged deps).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "constructor options sessionCookieValue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-before-merge with a stable error-prefix vocabulary for any tool whose options reach process/network level (fail before launch, not mid-scrape); adapt to schema libraries (zod/pydantic) as the option surface grows — the invariants to preserve are tested-message stability and defaults-that-survive-rejection; omit nothing. Python per-file flavor lives in `config-validation-ladder.md`; the auth-specific subset is already covered by `cookie-session-bootstrap.md`.
