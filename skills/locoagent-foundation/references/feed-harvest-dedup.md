<!-- capsule-v2 -->
# Feed harvest with ID-keyed dedup — how do you collect N unique targets from an infinite-scroll feed without duplicates or self-replies?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you turn one screenful-plus-one-scroll of a social feed into exactly N unique, other-people's post URLs?

## Load the matching source dump
**Path/Symbol:** `workflows/executors/x-search-reply.ts` Step 1 (`:248-320`): URL extraction eval (`:254-263`), own-post filter (`:273`), scroll-on-shortfall (`:276-297`), status-ID dedup (`:299-309`), quota slice (`:309`).
**Signature:** harvest → `string[]`; filters `h.match(/\/status\/\d+$/) && !h.includes('/photo/') && !h.includes('/analytics')`; dedup key = regex capture group 1 (the numeric status ID).
**Data Shape:** href list from `document.querySelectorAll('a[href*="/status/"]')` wrapped in `[...new Set(...)]` inside one `JSON.stringify` eval; final `posts` carry `{ url, content: '', replyText: '', replied: false, skippedDedup }`.

### Decisive source
```ts
// Filter out own posts — BEFORE quota math, so self-posts never consume budget
postUrls = postUrls.filter(u => !u.includes(`/${xUsername}/status/`))
// Scroll for more if needed (one extra round)
if (postUrls.length < config.maxPosts) { ab('scroll down 3'); ab('wait 2000'); /* re-eval, merge unseen */ }
// Deduplicate by STATUS ID (same post reachable via multiple UI surfaces/absolute URLs)
const seenIds = new Set<string>()
for (const url of postUrls) {
  const match = url.match(/\/status\/(\d+)$/)
  if (match && !seenIds.has(match[1]!)) { seenIds.add(match[1]!); uniqueUrls.push(url) }
}
postUrls = uniqueUrls.slice(0, config.maxPosts)
```

**Flow:** open the search feed on the Latest tab (`f=live`) → one eval collects all status hrefs as a JSON array (Set-deduped in-page) → drop links containing your own `/username/status/` → if below quota, scroll once, wait, re-collect, merge only NEW urls → dedup by the numeric status ID captured from the tail of the href → cap at `maxPosts` preserving first-seen order.
**Invariant:** Identity is the STATUS ID captured from the URL, not the raw href — the same post surfaces through multiple anchors and absolute forms and must collapse to one entry. Own-account exclusion happens BEFORE quota slicing so your own posts can never crowd out real targets. IDs serve as identity here (plain string Set is correct); BigInt sorting is only needed when ranking by recency (contrast: compose-self-reply.md `getPostUrl`).
**Probe:** No direct test for this executor (coverage caveat — source-grounded). Deterministic probes: grep pins the own-filter at `:273`, `seenIds` at `:300-305`, and the quota slice at `:309`; `search_graph` resolves `locoagent.workflows.executors.x-search-reply.main`; contrast confirmed against `getPostUrl` BigInt sort in compose-self-reply.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "status hrefs search feed scroll harvest seenIds", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt in-page Set collection via one JSON eval, own-content exclusion before quota math, one bounded scroll-and-merge round, and ID-capture dedup for any feed/list harvesting. Adapt selectors, the ID-bearing URL shape, and quota size. Omit the analytics/photo exclusions unless your target surface has the same noise link kinds.
