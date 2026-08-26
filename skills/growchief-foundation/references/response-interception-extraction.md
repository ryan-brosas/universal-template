<!-- capsule-v2 -->
# Response interception extraction — how are authenticated JSON APIs mined via network interception plus in-page fetch replay?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** the app needs structured lead data that only authenticated voyager/X endpoints return — how is it captured and paginated WITHOUT calling the API from Node?

## waitForResponse(queryId) → reuse request params → page.evaluate(fetch) with rewritten pagination
**Path/Symbol:** `shared/server/bots/providers/linkedin/linkedin.provider.ts:leadList` (:66-135); DOM twin raced in `processLead` (:160-258); extractors `extra.person.profile.ts:extractConnectionTarget` (:1-34) / `extract.my.profile.ts`.
**Signature:** `leadList(params): Promise<RequireField<ProgressResponse,'leads'>>`; in-page worker: `page.evaluate(async ({url, params}) => (await (await fetch(url, params)).json())?.included... , {url, params})`.
**Data Shape:** `listParams = { method, headers, postData }` cloned from the INTERCEPTED browser request (auth cookies/CSRF ride along automatically inside the page context); pagination via `url.replace(/start:\d*/gm, 'start:${num}')` over `[0,10,...,90]`.

### Decisive source
```ts
const response = await params.cursor.page.waitForResponse(/5ba32757c00b31aea747c8bebb92855c/gm,
  { timeout: 0 });                       // wait for THE voyager queryId hash
const request = response.request();
const listParams = { method: request.method(), headers: request.headers(),
                     postData: request.postData() };
for (const num of [0, 10, 20, ..., 90]) {
  const list = await params.page.evaluate(async ({ url, params }) => {
    const data = await (await fetch(url, params)).json();
    return (data?.included || [])?.filter((f) => f?.navigationUrl)?.map(...) || [];
  }, { url: newUrl, params: listParams });
  if (list.length === 0) break;          // empty-page latch ends pagination
  loadLeads.push(...list);
  await timer(2000);                      // humanized pacing between replays
}
return { ..., leads: uniqBy(loadLeads.filter((f) => f.url), (p) => p.url) };
```

**Flow:** user browses to a search page → provider waits for the specific query-hash response → clones its request identity → replays it INSIDE the page for offsets 0..90 until an empty page → dedupes by URL. `processLead` instead RACES two independent resolvers: the same queryId-interception path (`response.json()` → `extractConnectionTarget` reads `identityDashProfilesByMemberIdentity.*elements`, degree/pending scraped via `JSON.stringify(payload).match(/DISTANCE_(\d)/)` / `/PENDING/`) versus a pure-DOM top-card walker (verified-badge locator, `#clock-small` 500ms probe ⇒ pending invite) — whichever resolves first wins.
**Invariant:** all replayed fetches run in PAGE context so headers/cookies are first-party (Node-side replay would need cookie juggling and trip CSRF); the empty-page break must come BEFORE pushing (a zero-length list contributes nothing but signals exhaustion); query-id hashes are rotating product secrets — match by stable URL shape, never hardcode without a refresh plan.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'waitForResponse' shared/server/bots/providers/linkedin/linkedin.provider.ts` → :68/:167/:266; X twin `waitForResponse(/UserByScreenName/gm)` x.provider.ts:42; empty-latch `if (list.length === 0) break` → :126-128.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "leadList processLead waitForResponse included", limit: 10 });
```

## Verdict
Adopt: intercept-once-replay-many extraction with in-page execution and dual network/DOM racing. Adapt selectors/hashes per target site and add rotation handling. Omit verbatim query hashes and selector tables (product secrets).
