<!-- capsule-v2 -->
# networkidle2 readiness gate — which waitUntil actually guarantees lazy profile sections exist before parsing?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** Why is networkidle2 mandatory here when domcontentloaded feels faster — and what exactly breaks if you switch?

## Idle-network navigation gate
**Path/Symbol:** `src/index.ts:LinkedInProfileScraper.run` goto block (:518–526).
**Signature:** `await page.goto(profileUrl, { waitUntil: 'networkidle2', timeout })` — resolves when ≤2 requests have been in flight for ~500 ms.
**Data Shape:** governs BOTH navigation sites (`checkIfLoggedIn` probe navigates identically); timeout bounded by the shared `options.timeout` (default 10000 ms).

### Decisive source
```ts
await page.goto(profileUrl, {
  // Use "networkidl2" here and not "domcontentloaded". 
  // As with "domcontentloaded" some elements might not be loaded correctly, resulting in missing data.
  waitUntil: 'networkidle2',
  timeout: this.options.timeout
});
```

**Flow:** navigate until the network goes quiet (≤2 inflight) → ONLY THEN autoScroll, click the expander families, and run the five parse passes → anything not hydrated by then reads as absent.
**Invariant:** readiness is a DATA-COMPLETENESS invariant, not a tuning knob — domcontentloaded fails SILENTLY in this architecture: the null-preserving output schema converts unhydrated sections into null fields / empty arrays instead of errors, so a "faster" config quietly ships incomplete profiles.
**Probe:** no dedicated test — coverage caveat; deterministic source-comment pin: `grep -n 'networkidl2' src/index.ts` → :522; behavioral contrast is manual (a domcontentloaded run yields empty experience lists on slow-loading profiles).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "run profile scrape", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt idle-based readiness as the DEFAULT for SPA profile scrapes; adapt strictness to the target (networkidle0 stricter; custom idle windows in other drivers); omit domcontentloaded entirely wherever downstream consumers cannot distinguish null-as-missing-data from null-as-truly-empty.
