<!-- capsule-v2 -->
# Querystring repagination router — how do I re-page a SAVED search URL without disturbing anything but the query?

**Source:** linvo-scraper ISC `main@cfbe91080c73`; Codebase Memory `linvo-scraper`. **Question:** given a stored LinkedIn search URL (possibly hash-routed) and a target page number, how do you produce the next page's URL — and where do the guard rails go?

## LinkedinGlobalPageService.startProcess — query-only rewrite, wall, CSV bypass, sales routing
**Path/Symbol:** `lib/linkedin/linkedin.global.page.service.ts:LinkedinGlobalPageService.process` (:32–35) → `.startProcess` (:37–148; query rewrite :54–102; routing :104–107). Registered as `scraper` in the services registry.
**Signature:** `startProcess(page, cdp, data: { page: number; url: string; remove_overlapping: boolean }) -> { pages: number; values: PageConnections[]; csv?: string }`.
**Data Shape:** `PageConnections = { name, link, image, description, connect }`; page>100 or run=false short-circuits to `{values: [], pages: 0}`; precomputed S3 CSV urls pass through as `{csv: url, pages: 1}`.

### Decisive source
```ts
if (pageNumber > 100) return { values: [], pages: 0 };        // hard wall
const onlyQuery = new URL(url.replace("#", "?"));
const parseQuery = parse(onlyQuery.search);
if (pageNumber === 1) delete parseQuery.page;                  // canonical first page
else parseQuery.page = pageNumber;
if (parseQuery?.viewAllFilters) parseQuery.viewAllFilters = "false";
const newUrl = stringify(parseQuery,
  onlyQuery.origin + onlyQuery.pathname +
  (url.indexOf("#") > -1 ? "#" : "?"));                        // preserve hash routing
const info = await (url.indexOf("/sales/") > -1 ? salesPage : normalPage)
  .pagesTask(page, newUrl);
```

**Flow:** wall-check → parse stored URL treating `#` as query start → mutate ONLY the parsed query (`page` set/deleted, `viewAllFilters` forced false) → re-stringify against the ORIGINAL origin+pathname choosing `#` vs `?` separator from the input → route: `/sales/` in url ⇒ SalesNav `pagesTask`, else regular-feed `pagesTask`.
**Invariant:** the path/origin/hash STRUCTURE of a saved search is immutable — repagination touches the query component alone, and page 1 stays canonical by DELETING `page`; the >100 wall bounds DOM paging honestly (empty success, not error) mirroring API-side ~1000-result ceilings; routing by substring keeps Sales Nav and feed pipelines behind ONE entry.
**Probe:** no upstream tests (blocker). Deterministic anchor: `delete parseQuery.page` + separator-preserving two-arg `stringify` + >100 wall at HEAD — verification.md probe P8. HONEST CAVEATS: lines :115–147 (a `Promise.race` "No results found" watcher) sit AFTER an unconditional return — dead code; the S3 bucket prefix is linvo-infra-specific.
**Coverage caveat:** `check_index_coverage` = no_recorded_issue/metadata_match for the file; dead range verified by direct read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "startProcess pagesTask", limit: 5 });
```
Resolves `startProcess` :37–148 + BOTH `pagesTask` implementations (page.service :78–172, sales.page.service).

## Verdict
Adopt query-only rewriting with canonical page-1 deletion, the separator-preserving re-stringify, and the empty-success wall. Adapt the wall number to your target surface and drop the S3 bypass unless you own a precompute pipeline. Omit the dead race block entirely — and record similar unreachable watchers when you find them instead of porting them.
