<!-- capsule-v2 -->
# Expand-then-parse — when must a scraper click "see more" before extracting, and how does it stay tolerant of missing buttons?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** How do I materialize lazy/truncated content before parsing without a missing selector killing the run?

## Two click families + settle wait
**Path/Symbol:** `src/index.ts:LinkedInProfileScraper.run` (:536–578) — `expandButtonsSelectors` (4 unique-section buttons) then `seeMoreButtonsSelectors` (2 repeated-item clamps); precede by `autoScroll(page)` (:146–163 local twin of `utils/index.ts:152–169`).
**Signature:** `for (const s of expandButtonsSelectors) { if (await page.$(s) !== null) await page.click(s) }` wrapped per-selector in try/catch; then `await page.waitFor(100)` BEFORE the second family.
**Data Shape:** family 1 = one button per section (About `.lt-line-clamp__more`, Experience/Education `.pv-profile-section__see-more-inline`, Skills `[data-control-name="skill_details"]`); family 2 = N buttons per list (`page.$$` over `.lt-line-clamp__more[href="#"]`, skipping the dummy ellipsis via `:not(.lt-line-clamp__ellipsis--dummy)`).

### Decisive source
```ts
try {
  if (await page.$(buttonSelector) !== null) {
    await page.click(buttonSelector);
  }
} catch (err) { /* "Could not find or click ... So we skip that one." */ }
...
// To give a little room to let data appear. Setting this to 0 might result
// in "Node is detached from document" errors
await page.waitFor(100);
```

**Flow:** autoScroll to bottom first (loads every section into DOM) → family 1: presence-checked single clicks per section → 100ms settle (comment records WHY: 0ms yields "Node is detached from document") → family 2: enumerate ALL clamp buttons and click each inside its own try/catch → only THEN run the five `evaluate/$$eval` extraction passes.
**Invariant:** every click is individually skippable — a missing/removed button logs and moves on; expansion failures degrade data completeness but can NEVER abort the scrape. The two families are ordered because they serve different shapes (one gate per section vs. one clamp per item), and the settle-wait between them is load-bearing for detached-node avoidance.
**Probe:** no test covers the click ladder — source-grounded only. Selectors are era-specific (`pv-*` classes); the STRUCTURE is the portable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "LinkedInProfileScraper autoScroll", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scroll→expand→settle→parse as an ordered pipeline with per-click exception islands and an explicit settle wait. Adapt all selectors freely — they rot against live LinkedIn (same caveat as suite's `profile-section-expansion.md`, which is this repo's more advanced sibling). Omit nothing structural.
