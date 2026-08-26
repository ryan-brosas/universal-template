---
name: gnews
description: >-
  Search Google News through CDP. Returns structured results (title, URL,
  source, time, snippet) for any query — the publisher's direct URL, no
  news.google.com redirect wrapper. Use when the user asks for news,
  headlines, or recent coverage of a topic. Requires browser-harness-js on
  PATH and a Chromium-based browser with remote debugging enabled.
setup: bash <skill-dir>/scripts/setup
compatibility: >-
  Requires browser-harness-js on PATH and a running Chromium browser with
  remote debugging (chrome://inspect or --remote-debugging-port). No API key,
  no account.
---

# Google News

Search Google News and extract structured results via CDP. Hits Google Search's
news tab (`tbm=nws`) through the user's own browser, so the rendered page — not a
raw fetch — drives the extraction. No external dependencies beyond
`browser-harness-js` (which provides the CDP session). Each call opens its own
tab with a per-call `sessionId` — safe for parallel use.

## Quick search

```bash
gnews "your query"            # pretty-printed, up to 10 results
gnews "your query" 5          # 5 results, pretty-printed
gnews --json "your query" 3   # raw JSON
```

## Parallel use

Each `gnews` call reuses the shared WebSocket but attaches to its own tab with a per-call `sessionId`. Tab-specific CDP calls go through `cdp(sessionId, method, params)`. Multiple calls can run concurrently without interfering — no `activeSessionId` clobbering, no tab trampling, no event cross-fire. Tabs are closed fire-and-forget via `Target.closeTarget` so the caller isn't blocked waiting for cleanup.

```bash
gnews "rust async" 3 &
gnews "go channels" 3 &
wait
```

## Result shape

Each result is `{ title, url, source, snippet, time }`:

```json
[
  {
    "title": "Meta jumps into AI coding market in effort to chase Anthropic and OpenAI",
    "url": "https://www.cnbc.com/2026/07/09/meta-jumps-into-ai-coding-market.html",
    "source": "CNBC",
    "snippet": "Meta is upgrading its Muse Spark artificial intelligence models…",
    "time": "21 hours ago"
  }
]
```

The `url` is the **publisher's direct link** — `tbm=nws` returns the real article URL, not a `news.google.com/articles/<id>` redirect wrapper. `snippet` is empty on cards Google renders without a description; `time` is Google's relative-time string (e.g. `2 hours ago`), in the browser's UI locale.

`--json` mode always emits valid JSON: a 0-result query returns `[]` (the script stringifies the array itself rather than returning it, so the REPL's empty-array-to-`''` rendering can't produce a non-JSON payload for `jq` / `JSON.parse` callers).

## Following a result link

Open a result `url` directly through `browser-harness-js` — no need to re-search. Same connect/create-tab/evaluate flow as ad-hoc search, but navigate to the article and extract page text:

```bash
browser-harness-js <<'EOF'
if (!session.isConnected()) {
  try { await session.connect() } catch (e) { throw new Error("Cannot connect: " + e.message) }
}

const url = "https://www.example.com/some-article"
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
  const result = await cdp(sessionId, "Runtime.evaluate", {
    expression: 'document.querySelector("article, main")?.innerText || document.body.innerText',
    returnByValue: true
  })
  return result.result.value
} finally {
  session.closeTab(t.targetId, sessionId).catch(() => {})
}
EOF
```

- `article, main` skips nav/footer chrome; `document.body.innerText` is the fallback.
- **Wait strategy.** The example waits for `networkIdle` (500ms of no in-flight network requests) — the right default for content pages: it fires after `load` so it returns at least as much content, and it isn't blocked by hanging ad/analytics beacons the way `loadEventFired` is. Alternatives for specific page types:
  - `networkAlmostIdle` (250ms quiet window) — for pages with continuous XHR polling that never reach the full 500ms.
  - `loadEventFired` — when you genuinely need every subresource loaded (rare for text extraction).
  - A short post-ready `await new Promise(r => setTimeout(r, 1000))` before the evaluate — for pages that lazy-render content *after* `networkIdle` (e.g. SPA hydration, lazy image packs). Many publisher sites lazy-load the article body, so this 1s pad is often worth adding here.

## Ad-hoc search without the script

If `gnews` isn't on PATH, the same logic runs directly through `browser-harness-js`:

```bash
browser-harness-js <<'EOF'
if (!session.isConnected()) {
  try { await session.connect() } catch (e) { throw new Error("Cannot connect: " + e.message) }
}

const count = 10
const t = await session.Target.createTarget({ url: "about:blank", background: true })
const { sessionId } = await session.Target.attachToTarget({ targetId: t.targetId, flatten: true })

try {
  await cdp(sessionId, "Page.enable", {})
  await cdp(sessionId, "Page.setLifecycleEventsEnabled", { enabled: true })
  const ready = session.waitFor({ method: 'Page.lifecycleEvent', sessionId, predicate: (p) => p.name === 'networkIdle', timeoutMs: 30_000 })
  await cdp(sessionId, "Page.navigate", {
    url: "https://www.google.com/search?q=" + encodeURIComponent("your query") + "&tbm=nws&num=" + count
  })
  await ready

  const expression = `(() => {
    const ext = a => { try { return !/^(www\\.)?google\\./.test(new URL(a.href).hostname) } catch { return false } };
    const cards = [...document.querySelectorAll("a[href]")].filter(a => a.querySelector("div[role=heading]") && ext(a));
    const ex = a => {
      const title = (a.querySelector("div[role=heading]")?.textContent || "").trim();
      let lines = (a.innerText || "").replace(/\\u00a0/g, " ").split("\\n").map(s => s.trim()).filter(s => s.length > 0);
      let source = "";
      let rest = lines.slice();
      if (rest[0] && rest[0] !== title) { source = rest[0]; rest = rest.slice(1); }
      if (rest[0] === title) rest = rest.slice(1);
      const dot = rest.indexOf(".");
      let snippet = "", time = "";
      if (dot >= 0) { snippet = rest.slice(0, dot).join(" ").trim(); time = rest.slice(dot + 1).join(" ").trim(); }
      else { time = rest.length ? rest.join(" ").trim() : ""; }
      return { title, url: a.href, source, snippet, time };
    };
    return cards.slice(0, 10).map(ex);
  })()`

  const result = await cdp(sessionId, "Runtime.evaluate", { expression, returnByValue: true })
  const results = JSON.parse(result.result.value)
  return results.map(r => r.title + "\n  " + r.url + "\n  " + [r.source, r.time].filter(Boolean).join(" · ") + (r.snippet ? "\n  " + r.snippet : "")).join("\n\n")
} finally {
  session.closeTab(t.targetId, sessionId).catch(() => {})
}
EOF
```

## How it works

| Step | CDP call | What it does |
|------|----------|--------------|
| 1 | `session.connect()` (once) | Connect shared WebSocket to browser |
| 2 | `Target.createTarget({ background: true })` | Create an isolated background tab |
| 3 | `Target.attachToTarget` | Get per-call `sessionId` for tab-scoped routing |
| 4 | `cdp(sessionId, "Page.enable", …)` | Subscribe to page events |
| 5 | `cdp(sessionId, "Page.setLifecycleEventsEnabled", …)` | Enable lifecycle events — `networkIdle` won't fire without this |
| 6 | `session.waitFor('Page.lifecycleEvent' networkIdle)` armed BEFORE `cdp(sessionId, "Page.navigate", …)` | Race fix: arm the `networkIdle` wait before navigate (kills the load-already-fired race), then go to `google.com/search?q=…&tbm=nws&num=N` (URI-encoded via `encodeURIComponent` in JS) |
| 7 | `cdp(sessionId, "Runtime.evaluate", …)` | Single DOM query extracts all results |
| 8 | `closeTab` (fire-and-forget) | Tear down tab without blocking the response |

Each call takes ~2–3s (dominated by the `networkIdle` wait). The shared WebSocket means no repeated permission popups. URI encoding and output formatting happen in JS — no `jq` dependency.

## Why `tbm=nws` (the news tab) over `news.google.com`

The dedicated Google News app (`news.google.com/search?q=…`) is a heavy React SPA whose result links are wrapped in a `news.google.com/articles/<id>` redirect — to get the real publisher URL you must follow each redirect. Google Search's news tab (`google.com/search?…&tbm=nws`) is the *same* Google News vertical but served from the classic results host: it renders with the same lifecycle as a normal search (so `networkIdle` works the same way gsearch uses it), and each result's `href` is the **publisher's direct URL**. That is why `gnews` targets `tbm=nws`: less SPA hydration, no redirect wrapper, and the same navigate-and-wait shape as `gsearch`.

## Why `Runtime.evaluate` over the accessibility tree

Like `gsearch`, a single `Runtime.evaluate` with `querySelectorAll` returns all results in one CDP call (~5ms), far cheaper than walking Google's 1000+ node AX tree with per-node parent lookups. The extraction deliberately avoids Google's obfuscated class names (`WlydOe`, `sjVJQd`, …), which churn: it keeps `<a>` anchors that (a) contain a `div[role=heading]` and (b) link off-Google — both structural, not class-based, so a class rename won't break it.

## Parsing the card text

Each result card's `innerText` reads, line by line:

```
<source>
<title>
[<snippet>]
.
<time>
```

The title is read from `div[role=heading]` (a stable semantic hook). The standalone `.` line is Google's separator between the snippet and the trailing relative time — it's present only when the card has a snippet, so the parser splits on it: text before it is the snippet, text after is the time. Cards with no snippet are just `source / title / time`.

## No `jq` dependency

URI encoding uses `encodeURIComponent()` in JS and output formatting is done via `.map().join()` in the heredoc. The raw query is injected into a **quoted** heredoc as a `__GNEWS_QUERY__` placeholder and rewritten by `node` with `JSON.stringify` — so `&`, `$`, backticks, quotes, and non-ASCII in the query need no manual escaping, and the function-replacement (`c.replace(/__X__/g, () => JSON.stringify(v))`) dodges the `&`/`$` semantics that bash `${var//}` and JS `String.replace` both apply to plain replacement strings. The REPL's `renderResult` passes string returns through raw — no JSON wrapping — so bash just prints.

## Traps

- **Tab cleanup uses `try/finally` with fire-and-forget `closeTab`** — `closeTab` does `window.close()` + `Target.closeTarget` for thorough cleanup, wrapped in `finally` so it runs even on errors. The call is not awaited so it doesn't block the response. Under rapid parallel calls the close operations serialize in the session's `closeQueue`, but they don't block results.
- **`Page.enable()` AND `Page.setLifecycleEventsEnabled({ enabled: true })` must both be called** on each new tab. The latter is required for Chrome to emit any `Page.lifecycleEvent` — without it, the `networkIdle` wait times out every time.
- **`networkIdle` wait has a 30s timeout** — uses `session.waitFor()` instead of a raw promise, so a hung page doesn't leak the tab. The news tab is plain server-rendered HTML, so `networkIdle` fires reliably; if a regional variant polls forever, see `networkAlmostIdle` under "Following a result link".
- **The news tab does not paginate.** It returns roughly 10–15 results per page and ignores `num=` above that. Requesting `gnews "q" 30` returns whatever the page loaded (capped at your `count` in JS), not 30 — there is no next-page fetch.
- **Result count may be less than requested** — Google sometimes returns fewer results than `num=`, and breaking-news queries can return 0 on a slow cycle.
- **Google may serve a consent/cookie wall** in some regions — this returns 0 results. Check with a screenshot if results come back empty.
- **Titles are not `<h3>` on the news tab** — unlike the classic search results (`gsearch`), news results put the title in a `<div role="heading">`. The extraction keys off `role=heading`, not `h3`.
- **Multi-statement heredocs need `return`** — `browser-harness-js` auto-returns single expressions only.
