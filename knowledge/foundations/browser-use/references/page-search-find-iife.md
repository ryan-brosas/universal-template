<!-- capsule-v2 -->
# Zero-LLM page search/find JS IIFE injection — how do you grep a live page over CDP without an LLM call, safely?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does the tools service run agent-supplied search text/regex/CSS selectors inside the page without script-injection or regex-reDoS hazards?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `_SEARCH_PAGE_JS_BODY` (:208), `_FIND_ELEMENTS_JS_BODY` (:296), `_build_search_page_js` (:328), `_build_find_elements_js` (:351), `search_page` action (:1352), `find_elements` action (:1384).
**Signature:** `_build_search_page_js(pattern: str, regex: bool, case_sensitive: bool, context_chars: int, css_scope: str | None, max_results: int) -> str`.

### Decisive source
```python
# Parameter injection is via json.dumps into var declarations — NEVER string
# interpolation of user input into JS source:
params_js = (
    f'var PATTERN = {json.dumps(pattern)};\n'
    f'var IS_REGEX = {json.dumps(regex)};\n'
    f'var CSS_SCOPE = {json.dumps(css_scope)};\n'
)
return '(function() {\n' + params_js + _SEARCH_PAGE_JS_BODY + '\n})()'
```
```javascript
// Inside the IIFE: non-regex patterns are escaped char-class style before new RegExp
if (IS_REGEX) { re = new RegExp(PATTERN, flags); }
else { re = new RegExp(PATTERN.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), flags); }
// zero-length match guard prevents infinite loop:
if (match[0].length === 0) re.lastIndex++;
// results are capped but total counts ALL matches:
totalFound++; if (matches.length < MAX_RESULTS) { ... }
return {matches, total: totalFound, has_more: totalFound > MAX_RESULTS};
```

**Flow:** Python builds an IIFE with JSON-encoded params → single `Runtime.evaluate(returnByValue=True, awaitPromise=True)` on a cached CDP session → in-page TreeWalker concatenates visible text with node offsets (element path resolved per match) → JS returns a plain dict; every failure mode (bad scope selector, invalid regex, invalid CSS selector) returns `{error: ...}` INSIDE the value instead of throwing → Python checks `exceptionDetails`, then the embedded error key, then formats matches as numbered lines with context and a "... showing N of total" tail.
**Invariant:** all user-controlled strings enter the IIFE only through `json.dumps` (quote-safe); literal-search mode must escape the pattern before `new RegExp` or dots/brackets in agent queries silently become wildcards; `has_more` is derived from total>shown so pagination advice stays truthful.
**Probe:** `tests/ci/test_search_find.py` — literal vs regex (:169/:181), css_scope limiting (:195), case sensitivity pair (:209/:221), max_results cap (:232), no-match (:245), element_path presence (:256), invalid scope/selector error shapes (:268/:349), src/href property resolution (:425).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_build_search_page_js _build_find_elements_js search_page find_elements Runtime.evaluate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the JSON-dumps param injection + in-value error returns + capped-matches-with-true-total contract for any "grep the page" tool; adapt the formatter copy; omit the specific element-path format.
