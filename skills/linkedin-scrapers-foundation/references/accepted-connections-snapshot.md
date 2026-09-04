<!-- capsule-v2 -->
# Accepted-connections snapshot — how do I export newly accepted connections in one pass, normalized?

**Source:** linvo-scraper ISC `main@cfbe91080c73`; Codebase Memory `linvo-scraper`. **Question:** what is the minimal honest contract for scraping the "accepted invitations" network list, and where must URL normalization happen?

## LinkedinAcceptedConnectionsService.process/scrapeProfile — gated snapshot, in-evaluate slash strip
**Path/Symbol:** `lib/linkedin/linkedin.accepted.connection.request.service.ts:LinkedinAcceptedConnectionsService.process` (:10–27), `.scrapeProfile` (:29–52).
**Signature:** `process(page: Page): Promise<Array<{ name: string; url: string }>>`; inner evaluate maps `.mn-connection-card` nodes.
**Data Shape:** row → `{ name: trimmed .mn-connection-card__name text, url: anchor href minus ONE trailing slash }`; selector miss or timeout → `[]` (never throws).

### Decisive source
```ts
url: [elm.querySelector("a")?.getAttribute("href")].reduce((all, url) => {
  if (url[url.length - 1] === "/") {
    return url.slice(0, -1);
  }
  return url;
}, ""),
```

**Flow:** `gotoUrl(...mynetwork/invite-connect/connections/)` (unawaited, swallowed) → `waitForLoader` → wait `.mn-connection-card__details` with 10 s timeout → single `page.evaluate` snapshots ALL visible cards (name + slash-stripped href) → caller projects to `{name, url}`.
**Invariant:** trailing-slash stripping happens INSIDE the page evaluate so returned urls are join-ready canonical paths (`/in/slug`-style, no trailing `/`); empty-on-miss keeps the walker loop alive — a throttled or empty account yields `[]`, not a crash; HONEST LIMIT: this is a single-viewport snapshot, there is NO pagination loop here.
**Probe:** no upstream tests (blocker). Deterministic anchor: `.mn-connection-card` selector + reduce-based slash strip at HEAD — verification.md probe P3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", name_pattern: "LinkedinAcceptedConnectionsService.*", limit: 5 });
```
Resolves:   LinkedinAcceptedConnectionsService Class 6-53 1 2

## Verdict
Adopt normalize-inside-evaluate (normalization after the boundary means every consumer re-decides) and empty-array-on-miss; adapt the 10 s gate to your loader latch; omit nothing structural — but pair this seam with a scroller when you need MORE than one viewport (see skip-limit-scroller / created-before-scroller for the paging machines).
