<!-- capsule-v2 -->
# CDP active-lifecycle fast page — how do I stop Puppeteer from background-throttling my scrape tab mid-parse?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** Which page-creation steps keep a headless tab fully active (no timer throttling, no CSP friction) from the first millisecond?

## Factory-hardened page
**Path/Symbol:** `src/index.ts:LinkedInProfileScraper.createPage` (:302–315) — first-tab recycle + CDP block.
**Signature:** `const session = await page.target().createCDPSession()` → `session.send('Page.enable')` → `session.send('Page.setWebLifecycleState', { state: 'active' })`; preceded by `await page.setBypassCSP(true)`.
**Data Shape:** no inputs/outputs — per-page side effects applied inside the ONE page factory; every consumer (login probe, parse passes) receives an already-active page because raw `browser.newPage()` is never used elsewhere.

### Decisive source
```ts
// Use already open page
// This makes sure we don't have an extra open tab consuming memory
const firstPage = (await this.browser.pages())[0];
await firstPage.close();

// Method to create a faster Page
// From: https://github.com/shirshak55/scrapper-tools/blob/master/src/fastPage/index.ts#L113
const session = await page.target().createCDPSession()
await page.setBypassCSP(true)
await session.send('Page.enable');
await session.send('Page.setWebLifecycleState', {
  state: 'active',
});
```

**Flow:** newPage → enumerate browser pages and close the initial about:blank tab (an idle tab keeps a renderer alive) → bypass CSP so later injection cannot be blocked by page headers → enable the Page domain → FORCE the web lifecycle to `active` → only afterwards install interception budget, UA, viewport, session cookie.
**Invariant:** lifecycle forcing happens at CREATION time inside the single factory, never per-navigation; an unfocused/backgrounded tab otherwise freezes `setInterval` scroll timers and delayed hydration mid-scrape.
**Probe:** no automated test covers this path — coverage caveat; deterministic source pins: `grep -n 'setWebLifecycleState\|setBypassCSP\|createCDPSession' src/index.ts` → :309–315; behavioral check is manual (forced-active tab keeps timers firing while unfocused).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "createPage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt factory-level forcing (one place, every page) plus the initial-tab recycle as free memory hygiene; adapt the exact CDP verbs to your driver (Playwright: `context.newCDPSession(page)`; zendriver wraps domains its own way); omit nothing. Complements `request-interception-budget.md`, whose Probe line points HERE for these companion speed seams — this capsule closes that pointer.
