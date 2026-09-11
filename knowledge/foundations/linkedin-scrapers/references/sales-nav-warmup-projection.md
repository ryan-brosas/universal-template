<!-- capsule-v2 -->
# Sales Nav warmup projection — how do I turn a Sales Nav search URL into lead rows entirely from the first network response, and what must the browser survive first?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** what is the live pipeline from "stored sales-nav URL" to `{pages, values}` — including the session warm-up that must happen before the real navigation?

## LinkedinSalesPageService.pagesTask live plane (:15–116) — warm-up → six-marker response predicate → clamped projection
**Path/Symbol:** `lib/linkedin/linkedin.sales.page.service.ts:LinkedinSalesPageService.pagesTask` LIVE REGION ONLY :15–116 (post-:117 tail is unreachable; see post-return-stranded-dom-walk); router entry `linkedin.global.page.service.ts:startProcess` :104–107.
**Signature:** `pagesTask(page: Page, url: string): Promise<{pages: number, values: LeadRow[]}>`; `salesNavChooser(page)` (:6–13, guarded click-through of `.action-select-contract` when present).
**Data Shape:** output row `{premium: boolean, connected: boolean(degree===1), link: "https://www.linkedin.com/in/<id>" | undefined, name: "<first> <last>", image: rootUrl+artifact|"", description: summary|""}`; pages = `Math.ceil(min(paging.total, 2500)/25)`, 0 when no total.

### Decisive source
```ts
// WARM-UP: land on Sales Nav shell FIRST and wait for the SPA redirect
await page.goto("https://www.linkedin.com/sales/index", { waitUntil: "networkidle2" });
await page.waitForFunction(() =>
  window.location.href.indexOf("https://www.linkedin.com/sales/home") > -1);
await page.waitForSelector(".logo-text", { visible: true });
page.goto(url); this.salesNavChooser(page);

// RESPONSE PREDICATE: accept JSON OR the <code>-island HTML page, but the HTML
// arm requires SIX co-occurring markers before it will resolve
const res = await page.waitForResponse(async (p) => {
  try {
    const text = await p.text();
    return (p.headers()["content-type"] === "application/json"
              && text.includes("firstName") && text.includes("elements"))
        || (p.headers()["content-type"] === "text/html"
              && text.split("<code").some((f) =>
                   ["firstName","elements","premium","degree","summary","entityUrn"]
                     .every((m) => f.indexOf(m) > -1)));
  } catch (err) { return false; }
}, { timeout: 0 });                       // wait as long as it takes

return {
  pages: paging?.total ? Math.ceil((paging.total > 2500 ? 2500 : paging.total) / 25) : 0,
  values: elements
    ?.filter((f) => f?.firstName && f?.entityUrn?.includes("fs_salesProfile"))
    ?.map((e) => ({ premium: e?.premium,
                    connected: e?.degree === 1,
                    link: [e?.entityUrn?.split("(")[1]?.split(",")[0]?.trim()]
                            .filter(Boolean)
                            .map((f) => "https://www.linkedin.com/in/" + f).find(Boolean),
                    name: e.firstName + " " + e.lastName,
                    image: e?.profilePictureDisplayImage?.artifacts?.length
                             ? e.profilePictureDisplayImage.rootUrl +
                               e.profilePictureDisplayImage.artifacts[0].fileIdentifyingUrlPathSegment
                             : "",
                    description: e?.summary || "" }))
    ?.filter((f) => f?.link && f?.name) || [],
};
```

**Flow:** global.page router rewrites the query component then dispatches `/sales/` URLs here → warm-up navigation establishes an authenticated Sales Nav SPA session (index → /sales/home redirect latch → logo-text) → navigate target URL + chooser click-through → block on THE response that carries results (JSON arm: 2 markers; HTML arm: `<code>` island with all 6 markers) → decode via `res.json()` or in-page `<code>` extraction → clamp total at 2500 → project fs_salesProfile entities to canonical `/in/` links.
**Invariant:** nothing DOM-parsed is trusted for identity — every exported row's link derives from `entityUrn` (`split("(")[1].split(",")[0]`), and rows lacking a derivable link+name are dropped rather than emitted broken; `degree === 1` is the ONLY connected signal; the warm-up is not optional ceremony — without the index→home redirect the target navigation can hit an unauthenticated shell whose responses never satisfy the predicate. The unbounded `timeout: 0` makes the predicate the sole progress gate.
**Probe:** no upstream test runner exists at pin — recorded BLOCK; deterministic anchors executed instead: `grep -n "sales/index" lib/linkedin/linkedin.sales.page.service.ts` pins :16; `grep -n "fs_salesProfile" …` pins :97; `grep -n "2500" …` pins :91; `grep -n 'e?.degree === 1' …` pins :102.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "pagesTask waitForResponse firstName entityUrn premium degree", limit: 8 });
```

## Verdict
Adopt the warm-up-then-intercept order for any SPA behind its own auth shell, and the multi-marker HTML predicate as an anti-false-positive gate (a lone "elements" substring would match nav payloads); adapt the marker set and per-page count (25 here vs 10 in the feed twin embedded-json-search-parse) and the 2500 clamp to your wall policy; omit the dead post-return DOM-walk tail below :117 — it never runs. Relationship: response-interception owns the GENERIC substring-gated waitForResponse decoder; profile-schema owns the entityUrn split grammar; querystring-repagination-router owns how `url` got here. Coverage caveat: source-grounded probes only, zero upstream tests.
