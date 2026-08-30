<!-- capsule-v2 -->
# Embedded-JSON search parse — how do I get LinkedIn people-search results WITHOUT DOM scraping or an API client?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** where does the structured search payload live in a plain page response, and how do I extract it without launching rendered-DOM parsing?

## LinkedinPageService.pagesTask — read the raw response buffer, pull the LAST <code> blob, JSON.parse it
**Path/Symbol:** `lib/linkedin/linkedin.page.service.ts:LinkedinPageService.pagesTask` (:78–172); dead DOM-walk tail (:173–238) and orphan `elements()` (:10–76, zero callers repo-wide).
**Signature:** `async pagesTask(page: Page, url: string) -> {pages: number; values: Array<{name, link, description, image}>}`.
**Data Shape:** source HTML embeds `<code>` elements containing the voyager-style JSON (`included[]` entity array + `data.metadata.totalResultCount`). Image URLs are TWO-PIECE: `vectorImage.rootUrl + artifacts[0].fileIdentifyingUrlPathSegment`.

### Decisive source
```ts
const goto = await page.goto(url);
const json = await page.evaluate((val) => {
  const div = document.createElement("div");      // OFF-DOM: never attached
  div.innerHTML = val;                             // val = raw response BUFFER
  const findElements = Array.from(div.querySelectorAll("code"))?.filter(
    (a) =>
      a?.textContent?.indexOf("elements")! > -1 &&
      a?.textContent?.indexOf("totalResultCount")! > -1);
  if (findElements.length === 0) return "{}";
  return findElements[findElements.length - 1]?.textContent?.trim();
}, (await goto?.buffer())?.toString());

const { included, data } = JSON.parse(json || "{}");
if (!data || !included) return { pages: 0, values: [] };

return {
  pages: Math.ceil(
    (data?.metadata?.totalResultCount > 1000 ? 1000 : data?.metadata?.totalResultCount) / 10),
  values:
    included?.filter((f) => f?.title?.text)?.map((f) => ({
      name: f?.title?.text,
      link: f?.navigationUrl,
      description: f?.primarySubtitle?.text,
      image: f?.image?.attributes[0]?.detailDataUnion?.nonEntityProfilePicture
              ?.vectorImage?.rootUrl
        ? rootUrl + artifacts[0].fileIdentifyingUrlPathSegment : "",
    }))?.filter((f) => f?.name && f?.link && f?.link.indexOf("/in/") > -1) || [],
};
```
The `return` on the line above :173 makes EVERYTHING after it unreachable — the legacy DOM path (`elements()` recursive nth-child walk with per-row moveMouseAndScroll + connectability class check) is preserved but DEAD. `elements()` has no caller anywhere in the repo (verified by grep). Pagination math caps at LinkedIn's hard 1000-result ceiling then ÷10 per page; `/in/` link filter drops company/universal results.
**Flow:** goto(url) → take response buffer → off-DOM parse → filter `<code>` by twin needles (`elements` AND `totalResultCount`) → take the LAST match (newest embedded state) → JSON.parse with `"{}"` fallback → guard included+data → cap count → ceil÷10 pagination → map entities → `/in/`-only.
**Invariant:** parse happens on the RAW BUFFER in a detached element — the page never needs to finish rendering its React tree; missing blobs degrade to `{pages: 0, values: []}`, never throw. The 1000-cap is LinkedIn's server-side search ceiling — requesting beyond it is wasted motion, so fold it into page-count math BEFORE dividing.
**Probe:** no upstream tests (stub only) — caveat recorded; boundary verified by whole-file read at HEAD; graph anchor `LinkedinPageService.pagesTask` resolves :78–172 exactly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "pagesTask totalResultCount included code elements", limit: 5 });
// also surfaces LinkedinSalesPageService.pagesTask :15–197 (Sales Nav twin, already mined as sales-nav-pagination)
```

## Verdict
Adopt buffer→off-DOM `<code>`-blob extraction as the zero-API acquisition channel for public search surfaces (cheapest possible tier between full DOM scraping and authenticated voyager calls); adapt needle pairs and entity-field paths to current embedded schema versions; omit the dead `elements()` walk unless porting to a surface that serves NO embedded JSON (then it becomes live code again). Contrast: hassan/maximo3k Sales Nav scrapers drive paged UIs; this reads what the server ALREADY sent — same data, one round trip, no interaction fingerprint.
