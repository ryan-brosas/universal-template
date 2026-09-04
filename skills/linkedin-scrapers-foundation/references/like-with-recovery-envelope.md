<!-- capsule-v2 -->
# Like-with-recovery — how do you like a profile's top post while guaranteeing the identity payload survives every failure path?

**Source:** linvo-scraper ISC `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** what is the correct failure envelope when an engagement click may fail silently?

## Identity-first result, try-wrapped click
**Path/Symbol:** `lib/linkedin/linkedin.like.service.ts:LinkedinLikeService.process` (:18-77).
**Signature:** `process(page, cdp, { url })` → `Promise<{ linkedin_id, url }>` — SAME two-field envelope from visit-resolve.
**Data Shape:** success AND failure return identical shapes; the only difference is whether the like happened. Callers cannot distinguish — and must not need to.

### Decisive source
```ts
await page.goto("about:blank");            // ← reset BEFORE deep navigation
const newUrl = createLinkedinLink(onlyUrl, false);
gotoUrl(page, onlyUrl + "/detail/recent-activity/shares/");
try {
  await this.waitForLoader(page);
  await page.waitForSelector(".social-actions-button", { visible: true, timeout: 7000 });
  const all = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-urn]"))
      ?.reduce(… .querySelector(".social-actions-button")?.getAttribute("id") …)
      ?.filter((f) => f)?.slice(0, 1));     // FIRST post only
  if (!all.length) return { linkedin_id: createLinkedinLink(newUrl, false), url: theUrl };
  await this.moveAndClick(page, `#${all[0]}`);
  return { linkedin_id: createLinkedinLink(newUrl, false), url: theUrl };
} catch (err) {
  return { linkedin_id: createLinkedinLink(newUrl, false), url: theUrl };
}
```

**Flow:** resolve identity first (same ladder as visit: goto → loader → timer(8000) → href read-back → canonicalize) → **about:blank interstitial resets SPA state before deep-linking into /detail/recent-activity/shares/** → find `[data-urn]` posts, take `.social-actions-button` id of the FIRST → moveAndClick → return envelope; empty list OR thrown error → SAME envelope.
**Invariant:** the identity payload is computed BEFORE the risky region and returned identically on success/empty/error — engagement is fire-and-forget, never blocks the campaign record; about:blank precedes every deep navigation (SPA route pollution guard); only ONE post is ever liked (`slice(0,1)`), volume-bounded by construction.
**Probe:** no repo tests (source-grounded caveat); anchors verified in-source: about:blank :32, recent-activity deep-link :36, social-actions-button :41, data-urn reduce :47-53, slice(0,1) :59, moveAndClick :66.
**Retrieve:** `search_graph({project:"linvo-scraper", query:"LinkedinLikeService process", limit:6})`.

## Verdict
Adopt: compute-identity-first + uniform success/failure envelope + single-target volume bound + SPA-reset interstitial before deep links. Adapt selectors/timers/deep-link paths. Omit nothing behavioral. Complements `ghost-cursor-click-ladder` (the HOW of clicking) — this is the WHAT-survives-a-failure contract.
