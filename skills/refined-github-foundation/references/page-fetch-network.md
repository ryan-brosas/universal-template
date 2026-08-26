<!-- capsule-v2 -->
# fetch-dom + isomorphic-fetch — how do you fetch and slice a host page's DOM from a content script without CORS or Firefox breakage?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** When a feature needs markup from another page of the host site (or a raw text asset), where does the fetch run, what gets cached, and how do cross-origin/CSP realities change the call path?

## Memoized page-DOM fetch with optional selector slicing
**Path/Symbol:** `source/helpers/fetch-dom.ts:fetchDom` (:8–27).
**Signature:** `fetchDom(url: string): Promise<DocumentFragment>` / `fetchDom<Selector extends string>(url: string, selector: Selector): Promise<ParseSelector<Selector, HTMLElement> | undefined>` — overloads; default export is `mem(fetchDom)`, named export `fetchDomUncached` bypasses memo.
**Data Shape:** Returns a `DocumentFragment` (doma-parsed) or, with `selector`, the FIRST match via `$optional` (`undefined` when absent — callers must null-check). Cache key = URL string only.

### Decisive source
```ts
log.http(url);
const absoluteUrl = new URL(url, location.origin).href;
// Firefox `fetch`es from the content script, so relative URLs fail
const response = await fetch(absoluteUrl);
const dom = domify(await response.text());
if (selector) {
	return $optional(selector, dom);
}
return dom;
```

**Flow:** log → absolutize URL against `location.origin` (Firefox content scripts resolve relative URLs against an extension origin, not the page's) → plain `fetch` (same-origin to github.com because the script runs ON the page) → parse HTML into a fragment → optionally return only the first element matching `selector`.
**Invariant:** The default export is MEMOIZED for the content-script lifetime: repeated calls with the same URL never re-hit the network. Any call whose target page can legitimately change between calls (e.g. after editing a comment) MUST use `fetchDomUncached`. No status handling: non-2xx bodies are parsed as DOM like any other.
**Probe:** No direct unit test (network+DOM bound). Coverage caveat recorded in-capsule; behavior pinned by feature call sites and the sibling `selectors.test.ts` which re-implements the same fetch-and-slice shape for fixtures.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "fetchDom", limit: 10 });
// → refined-github.source.helpers.fetch-dom.fetchDom Function source/helpers/fetch-dom.ts 8-23
```

## Background-proxied text fetch (CSP escape hatch)
**Path/Symbol:** `source/helpers/isomorphic-fetch.ts:webextFetch` + `fetchText` (:9–21).
**Signature:** `webextFetch(url: string, options: RequestInit): Promise<string>`; `fetchText({url, options}: FetchParameters): Promise<string>`.
**Data Shape:** Returns body TEXT or `''` on any non-OK response (deliberate: "Likely a 404. Either way the response isn't the CSS we expect #8142") — empty string doubles as the failure signal.
**Decisive source:**
```ts
return isWebPage()
	// Firefox CSP issue: https://github.com/refined-github/refined-github/issues/8144
	? messageRuntime({fetchText: {url, options}})
	: fetchText({url, options});
```
**Flow:** if running in a real web page (content-script context), send `{fetchText}` to the extension BACKGROUND via `messageRuntime` and let it fetch (escapes page CSP that blocks cross-origin requests); otherwise (background/options/dev pages) fetch directly. `fetchText` maps non-OK → `''`.
**Invariant:** Callers must treat `''` as failure — there is no thrown error path. The context split is by `isWebPage()`, not browser brand: the same code serves Chrome direct-fetch and Firefox proxied-fetch.
**Probe:** No direct unit test (messaging-bound); caveat recorded. The background receiver lives in `background.ts` (see `feature-loader-lifecycle.md` for the messageRuntime plane).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "webextFetch", limit: 10 });
// → refined-github.source.helpers.isomorphic-fetch.webextFetch Function source/helpers/isomorphic-fetch.ts 16-21
```

## Verdict
Adopt both contracts for any extension that reads host-site subpages: absolutize-before-fetch + optional selector slice + memoized-by-URL default; route cross-origin text fetches through the background worker when page CSP bites, with `''`-as-failure. Adapt the cache scope (here: per-page-load memoize; swap in `webext-storage-cache` for cross-session), and the message channel name. Omit GitHub-specific `log.http` telemetry.
