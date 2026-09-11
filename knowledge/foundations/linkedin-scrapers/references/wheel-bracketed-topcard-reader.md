<!-- capsule-v2 -->
# Wheel-bracketed top-card reader — how do I scrape profile identity fields that render across TWO DOM generations?

**Source:** linvo-scraper ISC `main@cfbe91080c73`; Codebase Memory `linvo-scraper`. **Question:** how does one evaluate read name/title/company/location/headline reliably while lazy media loads, without pinning a single selector generation?

## LinkedinAbstractService.extractInformation — paired wheel bracket + fallback chains
**Path/Symbol:** `lib/linkedin/linkedin.abstract.service.ts:LinkedinAbstractService.extractInformation` (:254–365).
**Signature:** `extractInformation(page: Page): Promise<{ currentTitle, currentPositionLength, headline, location, profilePicture, name, last_name, companyName, currentCompanyPicture }>`.
**Data Shape:** every field resolves through an OR-chain of era-specific selectors and may be `undefined` — callers receive absent keys, never throws; name splits positionally into `name`/`last_name`.

### Decisive source
```ts
const name = (
  document?.querySelector(".text-heading-xlarge") ||            // current era
  document?.querySelector(".pv-top-card--list > li") ||          // legacy era
  { textContent: "" }
)?.textContent?.trim()?.split(" ");
const companyName = (
  document.querySelector(".pv-text-details__right-panel h2") ||
  document.querySelector(".pv-top-card--experience-list-item") || { textContent: "" }
)?.textContent?.trim();
```
Bracketing around the evaluate:
```ts
for (let i = 0; i < 4; i++) await page.mouse.wheel({ deltaY: 200 });   // down: wake lazy media
const info = await page.evaluate(() => { ...fallback chains... });
for (let i = 0; i < 4; i++) await page.mouse.wheel({ deltaY: -200 });  // up: restore position
await timer(3000);
```

**Flow:** four small real-mouse wheel steps DOWN (lazy images/headline mount) → ONE evaluate harvesting all nine fields via per-field fallback chains → four wheel steps UP (restore viewport for whatever action follows) → jittered 3 s settle → return info.
**Invariant:** reads happen INSIDE a single evaluate (one round-trip, consistent snapshot); each field degrades independently to undefined — a redesign of ONE field must not kill the other eight; the wheel bracket pairs MUST stay balanced so composite actions (visit→read→connect) inherit the original scroll position.
**Probe:** no upstream tests (blocker). Deterministic anchor: dual-era selector chains + balanced ±200×4 wheels at HEAD — verification.md probe P7.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "extractInformation", limit: 5 });
```
Resolves `LinkedinAbstractService.extractInformation` :254–365 rank 1.

## Verdict
Adopt per-field fallback chains with undefined-degradation and the balanced wheel bracket. Adapt selectors per DOM audit and replace the positional name split for multi-part names. Omit the hard-coded 4×200 wheel counts only if you have real scroll events — but keep SOME wake scroll before reading lazy top-card media.
