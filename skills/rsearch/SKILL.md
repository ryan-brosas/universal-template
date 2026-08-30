---
name: rsearch
disable-model-invocation: true
description: "Use when the user asks to search Reddit, find discussions or posts, or gauge community sentiment on a topic. Searches Reddit through the browser via CDP and returns title, subreddit, author, score, comments, permalink, and selftext, with optional subreddit and sort filters. No API key; a logged-in session is used automatically if present."
setup: bash <skill-dir>/scripts/setup
compatibility: >-
 Requires browser-harness-js on PATH and a running Chromium browser with
 remote debugging (chrome://inspect or --remote-debugging-port). No Reddit
 API key or app credentials, the in-page fetch rides the browser's reddit
 cookies (optional login).
---

# Reddit Search

Search Reddit posts through the browser: a background tab opens `www.reddit.com`, then a **same-origin** `fetch('/search.json?…', { credentials: 'include' })` hits reddit's own JSON listing endpoint with the browser's cookies, UA, and referer. Adapted from [opencli](https://github.com/jackwener/opencli)'s `clis/reddit/search.js`. No Reddit API key, no OAuth app, no scraping selectors, the response is reddit's canonical listing JSON. Each call opens its own tab and WebSocket session, safe for parallel use.

## Core Principle

Ask via the page, not from Node: a background tab opens `www.reddit.com`, then a
**same-origin** `fetch('/search.json?…', { credentials: 'include' })` hits reddit's own
JSON listing endpoint with the browser's cookies, UA, and referer. No Reddit API key,
no OAuth app, no scraping selectors, the response is reddit's canonical listing JSON.

## When to Use / NOT

- **Use when:** the user asks to search Reddit, find discussions or posts, or gauge
 community sentiment on a topic, any query, with optional subreddit restriction and
 sort/time filters. Works logged-out; a logged-in reddit session is used automatically
 if present.
- **NOT when:** the task is anything other than searching (posting, commenting, etc.),
 or no Chromium-based browser with remote debugging is running, the in-page fetch
 needs a committed `reddit.com` origin.

## Workflow

1. Ensure prerequisites: `browser-harness-js` on PATH and a running Chromium-based
 browser with remote debugging (`chrome://inspect` or `--remote-debugging-port`); run
 `bash <skill-dir>/scripts/setup` if not set up.
2. Run `rsearch "<query>" [count]` with flags before the query: `--json`,
 `--subreddit NAME`, `--sort S`, `--time T`.
3. Read the structured results (title, subreddit, author, score, comments, permalink
 URL, selftext, media URLs); link posts carry the external target in
 `url_overridden_by_dest`.
4. On persistent failure after the built-in retries, wait a bit or check the login
 state, it means real rate-limiting.

## Usage

```bash
rsearch "claude code"                                 # up to 15 results, pretty
rsearch "local llm" 5                                 # 5 results
rsearch --json "stable diffusion" 10                  # raw JSON array
rsearch --subreddit programming "git tips"            # within one subreddit (r/ prefix optional)
rsearch --sort top --time week "browser automation"   # sort + time filter

rsearch "rust async" 3 &                              # parallel-safe
rsearch "go channels" 3 &
wait
```

| Flag | Values | Default |
|------|--------|---------|
| `--json` |, | pretty text |
| `--subreddit NAME` | bare name, `r/name`, or `/r/name` | all of reddit |
| `--sort S` | `relevance` `hot` `top` `new` `comments` | `relevance` |
| `--time T` | `all` `hour` `day` `week` `month` `year` | `all` |
| positional 2 | count, 1–100 | 15 |

## Result shape

`--json` returns an array of posts, adapted 1:1 from opencli's column set:

```json
[
  {
    "id": "1abc2de",
    "title": "Show r/programming: …",
    "subreddit": "r/programming",
    "author": "someuser",
    "score": 1234,
    "comments": 210,
    "url": "https://www.reddit.com/r/programming/comments/1abc2de/…",
    "created_utc": 1735689600,
    "selftext": "…",
    "post_hint": "link",
    "url_overridden_by_dest": "https://example.com/article",
    "preview_image_url": "https://preview.redd.it/…",
    "gallery_urls": []
  }
]
```

Link posts carry the external target in `url_overridden_by_dest` (pretty output prints it after `->`); galleries list direct `i.redd.it` images in `gallery_urls`.

## Traps

- **Ask via the page, not from Node.** Server-side `fetch`/`curl` of `reddit.com/search.json` gets bot-walled or cookie-less default results. The in-page fetch runs with the browser's reddit cookies and real UA on a committed `reddit.com` origin, that's the whole trick. A logged-in session is used automatically; logged-out searches silently filter NSFW results.
- **Don't `waitFor('networkIdle')` on reddit.** The SPA polls continuously, so the 500 ms quiet window may never open. The script waits for the `Page.frameNavigated` **commit** (which fires regardless) plus a short `document.readyState` poll, the fetch only needs the committed origin, not a fully-built page.
- **Bound the page-side fetch.** CDP calls have no built-in timeout; the eval is raced against a 20 s node-side timeout so a hung reddit request fails instead of leaking the tab.
- **Non-JSON or non-200 responses surface as errors**, not empty results, e.g. `HTTP 403: Blocked` or a "non-JSON response … block or login wall" message. This fires only after the CLI has already retried twice with backoff: a fresh cookie jar's first `/search.json` hit gets a 403 interstitial whose response sets the cookies that make the retry pass. A persistent failure then means real rate limiting; wait a bit or check the login state.
- **Result count can be below `count`.** Reddit caps `limit` at 100 (the CLI clamps too) and often returns fewer, especially inside small subreddits.
- **Multi-flag ordering:** flags go before the query (`rsearch --sort top --time week "query"`), matching `gmaps`.

## Red Flags

- Server-side `fetch`/`curl` of `reddit.com/search.json` instead of the in-page fetch,
 bot-walled or cookie-less default results.
- `waitFor('networkIdle')` on reddit, the SPA polls continuously, so the quiet window
 may never open.
- An unbounded page-side fetch, CDP calls have no built-in timeout; the eval must be
 raced against the 20 s node-side timeout.
- Treating an empty result as success when the response was non-JSON or non-200, those
 surface as errors, not empty results.
- Expecting exactly `count` results, reddit caps `limit` at 100 and often returns
 fewer, especially inside small subreddits.
- Flags after the query, flags go before the query.

## Verification

- The command exits 0 and prints results (pretty text, or a raw JSON array with
 `--json`).
- Each result carries the expected fields: title, subreddit, author, score, comments,
 permalink URL, selftext, media URLs.
- A persistent error after the built-in retries means real rate-limiting, wait a bit or
 check the login state before retrying.

## Skill Result Contract

```
<skill_result>
  <skill><name></skill>
  <status>success|partial|blocked|failure</status>
  <evidence>…</evidence>
  <artifacts>…</artifacts>
  <risks>…</risks>
</skill_result>
```

## References

N/A, no reference files; usage, result shape, and traps are fully covered in this file.
