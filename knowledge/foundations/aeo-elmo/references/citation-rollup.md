<!-- capsule-v2 -->
# Citation rollup — how do two views answer "which sources, which domains, which categories" identically?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How should raw citation rows fold into URL/domain/category aggregates without double counting?

## Fold on normalized URL before classify
**Path/Symbol:** `apps/web/src/lib/citation-rollup.ts:rollUpCitationUrls` (L67–109), `rollUpCitationDomains` (L116–140), `tallyCitations` (L143–160).
**Signature:** `rollUpCitationUrls(rows: CitationUrlRow[], classify: (domain, url, title?) => CitationCategory): CitationUrl[]`.
**Data Shape:** rows `{url, domain, title, count, avg_position}`; folding key = `normalizeUrl(url)` (tracking params stripped) so the same page cited with and without UTMs is ONE source. Position math: `positionSum += avg_position × count; positionCount = avg_position != null ? count : 0` — rows without position contribute to count but not the average.

### Decisive source
```ts
// URLs are folded on their normalized form before classification: the same page
// cited with and without a tracking parameter is one source, and averaging
// positions across the pre-normalized rows would weight it twice.
const existing = folded.get(normalized);
if (existing) { existing.count += c; existing.positionSum += positionSum; existing.positionCount += positionCount; … }
```
Domains are REBUILT from folded URLs, each taking its category from its most-cited child URL ("so a domain that is mostly review articles reads as editorial rather than falling to 'other'"). Google-surface URLs are dropped throughout — they feed their own Google module and would otherwise be double-counted in the source mix.

**Flow:** brand-wide view adds period-over-period deltas; per-prompt view uses the rollup bare. The three questions live in this one module so the two views CANNOT answer differently.
**Probe:** covered by web app test suite (`citation-rollup` behaviors pinned via domain-categories fixtures); pure functions, no IO.
**Coverage caveat:** apps/web files verified via check_index_coverage no_recorded_issue; suite executed via repo vitest config in-repo, not in this capsule's minimal runner.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "rollUpCitationUrls rollUpCitationDomains tallyCitations normalizeUrl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt normalize-then-fold + weighted-position-average + category-by-dominant-child; adapt your classifier injection point (passed as a function); omit the Google-module carve-out if you have no special-cased surfaces.
