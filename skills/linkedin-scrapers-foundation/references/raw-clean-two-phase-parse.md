<!-- capsule-v2 -->
# Raw→clean two-phase parse — why does scraping split DOM extraction from text normalization across a serialization boundary?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** Where should text cleanup, date parsing, and geo classification live relative to the `page.evaluate` boundary — and why?

## Dumb browser, smart Node
**Path/Symbol:** `src/index.ts:run` — profile (:582–620), experiences (:626–695), education (:701–754), volunteer (:760–812), skills (:818–831); normalizers in `src/utils/index.ts` (getCleanText :129–144, getLocationFromText :44–127, formatDate :30–36).
**Signature:** `page.evaluate(() => RawX)` emits nullable `textContent` fields; then `{ ...raw, field: getCleanText(raw.field), location: raw.location ? getLocationFromText(raw.location) : null }` maps Raw→clean interface.
**Data Shape:** paired interfaces per section — `RawExperience`/`Experience`, etc.; clean variants ADD derived fields (`durationInDays`) and REPLACE raw strings with parsed structures (`location: string` → `Location {city, province, country}`).

### Decisive source
```ts
// Convert the raw data to clean data using our utils
// So we don't have to inject our util methods inside the browser context, which is too damn difficult using TypeScript
const userProfile: Profile = {
  ...rawUserProfileData,
  fullName: getCleanText(rawUserProfileData.fullName),
  location: rawUserProfileData.location ? getLocationFromText(rawUserProfileData.location) : null,
}
...
// Note: the $$eval context is the browser context.
// So custom methods you define in this file are not available within this $$eval.
```

**Flow:** `evaluate`/`$$eval` closures run in BROWSER context where module imports don't exist (both comments state this explicitly) → they do ONLY querySelector walks with `?.textContent || null` coalescing → serialized raw objects cross to Node → Node-side mapping applies regex cleanup (collapse spaces, strip line breaks/'...'/'See more'), date formatting, and geo classification.
**Invariant:** extraction closures stay DUMB; ALL intelligence stays in Node where it is unit-testable without a browser — `src/utils/index.test.ts` pins `formatDate`/`getDurationInDays`/`getLocationFromText` (incl. the two-part `'Sacramento, California Area'` ambiguity)/`getCleanText` directly. Every mapped field preserves nullability end-to-end: a missing DOM node becomes `null` in the OUTPUT schema, never a thrown error or empty string masquerading as data.

### Pinned-era baseline (pass-2 drift audit)
Every selector in the five passes is 2020-era vocabulary — `.pv-top-card`, `#experience-section ul > .ember-view`, `.pv-entity__*`, `.lt-line-clamp__*`, `.pv-skill-categories-section ol > .ember-view` — and upstream self-declares it: package.json description is literally "LinkedIn profile scraper returning structured profile data in JSON. **Works in 2020.**". The file's ONLY drift hedge is one OR-chain on the most-mobile field: `.pv-top-card__photo || .profile-photo-edit__preview` (:596). Treat this repo as the suite's pinned-era BASELINE for the two-plane discipline, not as a drift-defense source: redesign handling lives in `overview-vocabulary-classifier.md` (content-vocabulary classification), `wheel-bracketed-topcard-reader.md` (per-era fallback chains), and `profile-header-extraction.md` (attribute-carried state). Schema scope is closed and small at this pin — run() returns exactly `{userProfile, experiences, education, volunteerExperiences, skills}` (:850–856); peopleAlsoViewed/similarProfiles/accomplishments are ABSENT (token grep = zero hits), so accomplishment walking belongs to sibling capsules (`profile-section-expansion`, `update-extractor-family`).
**Probe:** `src/utils/index.test.ts` (pure-function matrix — runs without Puppeteer); the evaluate closures themselves are covered only by the dumbness invariant above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "getCleanText getLocationFromText evaluate raw", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the boundary rule for ANY Puppeteer/Playwright scrape: browser context extracts verbatim, Node normalizes and tests. Same instinct recurs across the suite (EasyApplyJobsBot answer cleaning, linvo post-processing) — this repo states it most explicitly. Adapt the specific normalizers to your locale/target. Omit nothing — pure architecture, no site coupling.
