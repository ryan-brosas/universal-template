<!-- capsule-v2 -->
# History cache & restore — how does htmx snapshot pages into sessionStorage and restore them on popstate?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** What is saved, when, under which key, and what is the miss ladder (server fetch vs full reload)?

## saveToHistoryCache / getCachedHistory / restoreHistory: LRU in one sessionStorage key
**Path/Symbol:** `src/htmx.js:saveToHistoryCache` (:3157-3203) + `getCachedHistory` (:3217-3231) + `restoreHistory` (:3341-3365) + `loadHistoryFromServer` (:3309-3336) + snapshot cleaning `cleanInnerHtmlForHistory` (:3237-3248) + popstate wiring in the ready block (:5131-5148); path normalization `normalizePath` (:846-858).
**Signature:** `function saveToHistoryCache(url, rootElt)`; items are `{url, content, title, scroll}`; key literal `'htmx-history-cache'`; current-path mirror `'htmx-current-path-for-history'`.
**Data Shape:** Cache is a JSON array, newest LAST, capped by `config.historyCacheSize` (default 10) via shift(); URL matching runs AFTER normalizePath (pathname+search, trailing-slash strip except `/`, malformed-URL fallback to raw path).

### Decisive source
```js
historyCache.push(newHistoryItem)
while (historyCache.length > htmx.config.historyCacheSize) { historyCache.shift() }
// keep trying to save the cache until it succeeds or is empty
while (historyCache.length > 0) {
  try { sessionStorage.setItem('htmx-history-cache', JSON.stringify(historyCache)); break }
  catch (e) {
    triggerErrorEvent(getDocument().body, 'htmx:historyCacheError', { cause: e, cache: historyCache })
    historyCache.shift() // shrink the cache and retry
  }
}
```

Miss ladder (`restoreHistory`): save current page first → normalized lookup → HIT ⇒ htmx:historyCacheHit (vetoable) then swap cached content with `{scroll: cached.scroll}` → MISS ⇒ `refreshOnHistoryMoney... config.refreshOnHistoryMiss ? location.reload : loadHistoryFromServer` (GET with HX-History-Restore-Request:true, HX-Request per historyRestoreAsHxRequest, swap innerHTML of `[hx-history-elt]||body`, events historyCacheMiss/MissLoad/Restore).
**Flow (snapshot):** before a push/replace (beforeSwapCallback) or on popstate, `saveCurrentPageToHistory` picks `[hx-history-elt]||body`, refuses ENTIRELY if any `[hx-history="false" i]` exists in the document (privacy embargo), cleans the clone (strip requestClass + `data-disabled-by-htmx`), captures scrollY+title, dedupes same-URL entries, fires htmx:historyItemCreated.
**Invariant:** Quota errors SHRINK AND RETRY rather than dropping the whole save — the newest entry survives at minimum. Popstate only handles state.htmx truthy entries; foreign popstates delegate to any pre-existing window.onpopstate (captured before override). Restores swap with settleDelay 0 and re-fire `htmx:restored` on `[hx-trigger=restored]` elements.

**Probe:** `test/attributes/hx-push-url.js`: "cache should only store 10 entries" :103, "cache miss should issue another GET" :119, "cache miss should refresh when refreshOnHistoryMiss true" :143, "deals with malformed JSON in history cache when getting/saving" :165/:171, "does not blow out cache when saving a URL twice" :178, "setting history cache size to 0 clears cache" :187, "history cache is LRU" :198, quota-safety "saveToHistoryCache should not throw" :248, sessionStorage-disabled tolerance :265, disabled-attribute cleanup :292 ("history cache clears out disabled attribute"). Privacy embargo: `test/attributes/hx-history.js` "history cache should not contain embargoed content" :11. Perf guards: `test/core/perf.js` :32/:50. Executed headless: normalizePath battery (`'/a/b/'→'/a/b'`, `'/'→'/'`).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "history cache sessionStorage save restore popstate", limit: 4 });
```
(rank-1 `src.htmx.saveToHistoryCache src/htmx.js 3157-3203`)

## Verdict
Adopt the single-key LRU with shrink-retry and the embargo check; both encode hard-won production behavior. Adapt sessionStorage to your storage layer (the canAccessLocalStorage probe pattern matters for Safari private mode). Omit refreshOnHistoryMiss only if server-rendered misses are acceptable.
