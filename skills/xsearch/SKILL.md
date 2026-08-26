---
name: xsearch
description: >-
  Search X (Twitter) via CDP. Returns structured results (author, handle, text,
  URL, timestamp) for any query. Requires browser-harness-js on PATH, a
  Chromium-based browser with remote debugging, and an active X session (logged in).
setup: bash <skill-dir>/scripts/setup
compatibility: Requires browser-harness-js on PATH, a running Chromium browser with remote debugging (chrome://inspect or --remote-debugging-port), and an active X (Twitter) login in the browser.
---

# X Search

> ⚠️ **You must be logged in to X in the browser.** X's search page does not show results to logged-out visitors — it redirects to a login wall. The browser session used by `browser-harness-js` must have an active X login.

Search X (Twitter) and extract structured results via CDP. No external dependencies beyond `browser-harness-js` (which provides the CDP session). Each call opens its own tab and WebSocket session — safe for parallel use.

## Quick search

```bash
xsearch "your query"             # pretty-printed, up to 10 results
xsearch "your query" 5           # 5 results, pretty-printed
xsearch --json "your query" 3   # raw JSON
```

## Parallel use

Each `xsearch` call reuses the shared WebSocket but attaches to its own tab with a per-call `sessionId`. Tabs are closed fire-and-forget via `Target.closeTarget` so the caller isn't blocked waiting for cleanup.

```bash
xsearch "rust async" 3 &
xsearch "go channels" 3 &
wait
```

## Result shape

Each result is `{ author, handle, text, url, time }`:

```json
[
  {
    "author": "Zane Chee",
    "handle": "@injaneity",
    "text": "people of pi, i'm excited to finally introduce browser use in pi-computer-use!",
    "url": "https://x.com/injaneity/status/2065110712511500620",
    "time": "2026-06-11T16:35:36.000Z"
  }
]
```

## Viewing an X post by URL

Open a result `url` (or any `x.com/<handle>/status/<id>` permalink) directly through
`browser-harness-js` — no need to re-search. Same connect/create-tab/evaluate flow
as ad-hoc search, reusing the `[data-testid="tweet"]` selectors but taking only
the focus tweet (first in DOM order on a permalink):

```bash
browser-harness-js <<'EOF'
if (!session.isConnected()) {
  try { await session.connect() } catch (e) { throw new Error("Cannot connect: " + e.message) }
}

const url = "https://x.com/injaneity/status/2065110712511500620"
const t = await session.Target.createTarget({ url: "about:blank", background: true })
const { sessionId } = await session.Target.attachToTarget({ targetId: t.targetId, flatten: true })

try {
  await cdp(sessionId, "Page.enable", {})
  // Required — without this Chrome emits zero Page.lifecycleEvent, so networkIdle
  // would never fire.
  await cdp(sessionId, "Page.setLifecycleEventsEnabled", { enabled: true })
  // Arm the wait BEFORE Page.navigate: lifecycle events fire once, and a fast
  // load can fire networkIdle between navigate returning and the listener subscribing.
  const ready = session.waitFor({ method: 'Page.lifecycleEvent', sessionId, predicate: (p) => p.name === 'networkIdle', timeoutMs: 30_000 })
  await cdp(sessionId, "Page.navigate", { url })
  await ready
  await new Promise(r => setTimeout(r, 4000))   // React hydration; see Traps

  const result = await cdp(sessionId, "Runtime.evaluate", {
    expression: `(() => {
      const el = document.querySelector('[data-testid="tweet"]')
      if (!el) return JSON.stringify(null)
      const textEl = el.querySelector('[data-testid="tweetText"]')
      const timeEl = el.querySelector('time')
      const userNamesEl = el.querySelector('[data-testid="User-Name"]')
      const nameLinks = userNamesEl ? [...userNamesEl.querySelectorAll('a[role="link"]')] : []
      return JSON.stringify({
        author: nameLinks[0]?.textContent?.trim() || "",
        handle: nameLinks[1]?.textContent?.trim() || "",
        text: textEl?.innerText?.trim() || "",
        time: timeEl?.getAttribute('datetime') || ""
      })
    })()`,
    returnByValue: true
  })
  return result.result.value
} finally {
  session.closeTab(t.targetId, sessionId).catch(() => {})
}
EOF
```

- The focus tweet (the one the permalink points to) is the first `[data-testid="tweet"]`
  in DOM order; replies and quoted tweets render below it.
- The 4s hydration wait matches `xsearch` — `networkIdle` fires before React renders
  tweets. Logged-out visitors hit a sign-in wall on permalinks too, same as search.
- **Wait strategy.** The example waits for `networkIdle` (500ms of no in-flight
  network requests) — the right default for X pages and most content sites: it
  fires after `load` so it returns at least as much content, and it isn't blocked
  by hanging ad/analytics beacons the way `loadEventFired` is. Alternatives for
  specific page types:
  - `networkAlmostIdle` (250ms quiet window) — for pages with continuous XHR
    polling that never reach the full 500ms.
  - `loadEventFired` — when you genuinely need every subresource loaded (rare for
    text extraction).
  - A short post-ready `await new Promise(r => setTimeout(r, 1000))` before the
    evaluate — for pages that lazy-render content *after* `networkIdle`.

## How it works

| Step | CDP call | What it does |
|------|----------|--------------|
| 1 | `session.connect()` (once) | Connect shared WebSocket to browser |
| 2 | `Target.createTarget({ background: true })` | Create an isolated background tab |
| 3 | `Target.attachToTarget` | Get per-call `sessionId` for tab-scoped routing |
| 4 | `cdp(sessionId, "Page.enable", …)` | Subscribe to page events |
| 5 | `cdp(sessionId, "Page.setLifecycleEventsEnabled", …)` | Enable lifecycle events — `networkIdle` won't fire without this |
| 6 | `session.waitFor('Page.lifecycleEvent' networkIdle)` armed BEFORE `cdp(sessionId, "Page.navigate", …)` | Race fix: arm the `networkIdle` wait before navigate (kills the load-already-fired race), then go to `x.com/search?q=…&src=typed_query&f=top` |
| 7 | `setTimeout(4000)` | Wait for React hydration and tweet rendering |
| 8 | Scroll loop (if count > 6) | Scroll to load more tweets (~3 per scroll) |
| 9 | `cdp(sessionId, "Runtime.evaluate", …)` | Single DOM query via `data-testid` selectors |
| 10 | `closeTab` (fire-and-forget) | Tear down tab without blocking the response |

## DOM selectors used

X's search page uses stable `data-testid` attributes:

| Selector | Purpose |
|----------|---------|
| `[data-testid="tweet"]` | Tweet container |
| `[data-testid="tweetText"]` | Tweet body text |
| `[data-testid="User-Name"]` | Author name/handle block |
| `a[role="link"]` within User-Name | Links: [0]=name, [1]=handle, [2]=permalink+timestamp |
| `time` | ISO timestamp via `datetime` attribute |

## Traps

- **You must be logged in.** X shows no search results to logged-out visitors — it redirects to a sign-in prompt. The browser session must have an active X login.
- **React hydration delay.** `networkIdle` fires before React renders tweets. A 4s wait after the ready signal is required for the initial batch (~6 tweets) to appear.
- **Scroll-to-load for more results.** X uses infinite scroll. The initial view contains ~6 tweets. For `count > 6`, the script scrolls down (each scroll loads ~3 more tweets with a 1.5s delay).
- **`Page.enable()` AND `Page.setLifecycleEventsEnabled({ enabled: true })` must both be called** on each new tab. The latter is required for Chrome to emit any `Page.lifecycleEvent` — without it, the `networkIdle` wait times out every time.
- **`networkIdle` wait has a 30s timeout** — uses `session.waitFor()` instead of a raw promise, so a hung page doesn't leak the tab. X loads continuously, but its initial network burst quiets down in ~2–3s in practice; if a page never reaches the 500ms quiet window, use `networkAlmostIdle` instead (see the wait-strategy note above).
- **Result count may be less than requested** — X may not have enough matching tweets, or the scroll loop may not load them in time.
- **Tweet text may be truncated** — X renders "Show more" buttons for long tweets. The extracted `text` is what's visible without clicking "Show more".
- **No `jq` dependency** — URI encoding uses `encodeURIComponent()` in JS and output formatting is done via `.map().join()` in the heredoc.
