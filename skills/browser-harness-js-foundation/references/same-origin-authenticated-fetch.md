<!-- capsule-v2 -->
# Same-Origin Authenticated Fetch — the browser session IS the API key

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How do the data skills call bot-walled JSON APIs (Reddit search.json, Yahoo chart, SEC EDGAR) keylessly?

## Path / Symbol
- rsearch: origin-commit then in-page `fetch("/search.json?...", {credentials:"include"})` — scripts/rsearch :131-152 (commit wait), :154-163 (readyState poll), :165-216 (fetch + 403-retry ladder + projection).
- findata: `navJsonFetch` → same-origin `fetch(window.location.href)` :160-186; ticker-map cache on `globalThis.__secTickerMap` :227-236.

## Signature
```js
// 1. Establish the origin with a real navigation (cookies/UA/referer become the browser's own)
await cdp(sid,'Page.navigate',{url:'https://www.reddit.com/'});
// wait main-frame frameNavigated matching /^https:\/\/([^/]*\.)?reddit\.com\// — commit, NOT networkIdle:
// "reddit's SPA keeps polling, so the network quiet-window can take forever to open,
//  and the fetch only needs the committed origin"
// 2. Fetch SAME-ORIGIN from inside the page
const res = await fetch(url, { credentials: "include" });   // cookies ride along; logged-in or not
```

## Data Shape
rsearch projects Reddit's envelope to `{id,title,subreddit,author,score,comments,url,created_utc,selftext,post_hint,url_overridden_by_dest,preview_image_url,gallery_urls[]}` with `decodeHtml` entity unescaping and gallery media_id→media_metadata join — projection happens IN-PAGE so only the small result crosses CDP.

## Decisive source
- The 403-first-hit retry ladder (rsearch :190-194): "Reddit 403s the very first search.json hit from a fresh cookie jar (anti-bot interstitial); **the 403 response itself sets the cookies that make the retry pass**, so back off briefly and retry" — 3 attempts, backoff 800ms×(attempt+1), non-JSON/!res.ok surfaced as a structured error string, never a raw throw.
- CDP eval timeout race (:216-219): "CDP calls have no built-in timeout — a page-side fetch that hangs would hang forever, so bound the eval with a node-side Promise.race."
- findata ticker-map memo (:229-236): cache on `globalThis.__secTickerMap` "for the server's lifetime (one fetch per session)" — recently listed tickers need `browser-harness-js --restart` (documented consequence).
- Why browser transport at all: findata SKILL.md "curl is blocked by bot protection on every free price site; the browser bypasses it" and rsearch header "curl/server-side fetches get bot-walled, this doesn't."

## Flow / Invariant
1. Navigate first (cheap URL), fetch second (authenticated, same-origin) — never try to set cookies by hand.
2. Treat the FIRST request's failure as cookie-seeding: retry with backoff before concluding blocked.
3. Project/filter in-page; cross the CDP boundary once, small.

## Probe (direct tests)
Live-browser egress was blocked in this sandbox (in-page fetch to example.com failed), so the fetch ladder itself is pinned statically at this pass: line-range reads above + smoke harness `bash skills/rsearch/scripts/test` exists for a networked host. Deterministic probes at pin: `grep -c 'credentials: "include"' skills/rsearch/scripts/rsearch` → 2 lines (:15 doc-comment example, :188 real fetch call); `grep -o "__secTickerMap" skills/findata/scripts/findata | wc -l` → 3 occurrences on 2 lines (:229 memoized read, :231 write) — ERRATUM pass-5 execution audit: shipped as "→ 1 / → 3"; live counts at unchanged pin `main@6b189406` are 2 lines / 3-occurrences-on-2-lines (comment hit + multi-mention line; re-derived against source). Smoke harness `bash skills/rsearch/scripts/test` exists for a networked host.

## Retrieve
grep-first (`credentials`, `search.json`, `__secTickerMap`).

## Verdict
ADOPT: navigation-as-authentication + 403-seeds-cookies retry is the reusable pattern for any login-optional bot-walled JSON API.
