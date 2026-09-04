<!-- capsule-v2 -->
# Endorse unchecked + close popover — how do I bulk-endorse a profile's skills without stale handles or blocked clicks?

**Source:** linvo-scraper ISC `main@cfbe91080c73`; Codebase Memory `linvo-scraper`. **Question:** when one page lists N not-yet-endorsed skill buttons, how do you click them all when each success opens a popover that intercepts the next click?

## LinkedinEndorseService.process — collect IDs once, click, close hoverable, repeat
**Path/Symbol:** `lib/linkedin/linkedin.endorse.service.ts:LinkedinEndorseService.process` (:23–98; unchecked collection :67–75; click+close loop :81–88).
**Signature:** `process(page: Page, cdp: CDPSession, data: { url: string }) -> Promise<{ linkedin_id: string; url: string }>`.
**Data Shape:** input url may be bare (`/in/slug`) or absolute → `createLinkedinLink(url, true)`; output is the standard identity envelope derived from `window.location.href` after the loop OR inside the catch — never the input URL.

### Decisive source
```ts
const all = await page.evaluate(() => {
  return Array.from(
    document.querySelectorAll(
      ".pv-skill-entity__featured-endorse-button-shared:not(.pv-skill-entity__featured-endorse-button-shared--checked)"
    )
  )?.map((p) => p.getAttribute("id")).filter((f) => f);
});
if (!all.length) {
  return { linkedin_id: createLinkedinLink(newUrl, false), url: newUrl }; // nothing unchecked ⇒ done
}
for (const id of all) {
  await this.moveAndClick(page, \`#\${id}\`);
  await page.waitForSelector(".artdeco-hoverable-content__close-btn");
  await this.moveAndClick(page, \`.artdeco-hoverable-content__close-btn\`);
  await timer(2000);
}
```

**Flow:** unawaited `gotoUrl` → `waitForLoader` → wait top-card selector → timer(3000) → ONE full-body `page.mouse.wheel({ deltaY: scrollHeight })` forces the lazy skills section → timer(3000) → wait `.pv-skill-categories-section` visible (7s) → `moveMouseAndScroll(section, 0, false, -200)` cursor glide → timer(4000) → collect UNCHECKED button ids in-page → per id: ghost-cursor click `#id` → WAIT for the hoverable's close button → click it → timer(2000) → return `{linkedin_id, url}`.
**Invariant:** only `:not(--checked)` buttons are targets, so re-runs are idempotent no-ops; EVERY successful endorse opens an `.artdeco-hoverable-content` that MUST be closed before the next click or it absorbs subsequent clicks; zero unchecked is a SUCCESS empty result, and ANY throw still returns the identity envelope (catch re-reads href) — the same recovery-envelope contract as like/connect.
**Probe:** repo ships no tests (lane blocker recorded). Deterministic anchor: byte-exact `:not(--checked)` selector at HEAD — see linvo-scraper-work/verification.md probe P1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "endorse", limit: 5 });
```
Resolves `LinkedinEndorseService.process` :23–98 rank 1.

## Verdict
Adopt the unchecked-only filter plus collect-ids-then-click-by-id (element handles would go stale across layout shifts from each popover), and the mandatory popover-close between iterations. Adapt selectors and the 2–4 s fixed timers (rot against live LinkedIn; replace with loader-latch waits). Omit linvo's swallow-everything catch if your scheduler needs typed failures — but still return identity on error.
