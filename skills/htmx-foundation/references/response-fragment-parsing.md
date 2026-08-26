<!-- capsule-v2 -->
# Response fragment parsing — how does htmx decide how to parse a partial response, and what happens to titles and scripts?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** Why are there THREE parse paths for response HTML (html/body/template-wrap), and where must the porter replicate title extraction and script re-creation?

## makeFragment: start-tag dispatch with head stripping
**Path/Symbol:** `src/htmx.js:makeFragment` (:603-644) + `getStartTag` (:513-521) + `parseHTML` (:527-533, prefers `Document.parseHTMLUnsafe`, falls back to DOMParser) + `takeChildrenFor` (:539-543) + `normalizeScriptTags` (:577-591).
**Signature:** `function makeFragment(response)` → `DocumentFragment & {title?: string}`.
**Data Shape:** Input is raw response text. Output fragment carries an extra `title` property. The `<head>` is stripped by regex FIRST (`response.replace(/<head(\s[^>]*)?>[\s\S]*?<\/head>/i, '')`) so head-only responses don't confuse shape detection; the start tag of the STRIPPED text decides the path.

### Decisive source
```js
const responseWithNoHead = response.replace(/<head(\s[^>]*)?>[\s\S]*?<\/head>/i, '')
const startTag = getStartTag(responseWithNoHead)
if (startTag === 'html') {
  // full document: parse it, return body's children
  fragment = new DocumentFragment()
  const doc = parseHTML(response)
  takeChildrenFor(fragment, doc.body)
  fragment.title = doc.title
} else if (startTag === 'body') {
  // parse body WITHOUT template wrapping
  ...
} else {
  // non-body partial: wrap in a template to maximize parsing flexibility
  const doc = parseHTML('<body><template class="internal-htmx-wrapper">' + responseWithNoHead + '</template></body>')
  fragment = doc.querySelector('template').content
  fragment.title = doc.title
  var titleElement = fragment.querySelector('title')
  if (titleElement && titleElement.parentNode === fragment) {
    titleElement.remove()
    fragment.title = titleElement.innerText
  }
}
if (fragment) {
  if (htmx.config.allowScriptTags) { normalizeScriptTags(fragment) }
  else { fragment.querySelectorAll('script').forEach((script) => script.remove()) }
}
```

**Flow:** strip head → sniff first start tag → html path / body path / template-wrap path → hoist title into `fragment.title` → script pass: either re-create every JavaScript script node (`type ''|'text/javascript'|'module'`) via `duplicateScript` (`async=false`, nonce applied from `config.inlineScriptNonce`) inserted BEFORE the original which is then removed — or remove all scripts when `allowScriptTags=false`.
**Invariant:** The template wrap exists because browsers parse table-row/option fragments differently outside template context ("janky stuff": bare `<td>`, `<tr>`, `<col>`, `<thead>` must survive as those tags). Script RE-CREATION (not cloning-in-place) is load-bearing: scripts created inside `<template>` content do not execute on insertion in some engines; a fresh element node does execute. Title precedence: root-level `<title>` in a non-body partial is removed from the fragment and moved into `.title`; SVG inner titles must NOT win (the `parentNode === fragment` guard). `swap()` later honors `swapOptions.title || fragment.title` only when `!swapSpec.ignoreTitle`.

**Probe:** `grep -n "makeFragment works with janky stuff" /mnt/hdd/utopia/inspo/external/htmx/test/core/internals.js` → :12 (asserts `<td>` parses to tagName TD etc.); "makeFragment works with template wrapping" :24. Script-once semantics: `test/core/regressions.js` "script tags only execute once" :206 and nested :222; disable path "htmx.config.allowScriptTags properly disables script tags" :238/:256. Title boundaries: `test/core/ajax.js` "title tags update title" :845, "svg title tags do not update title" :856, "first title tag outside svg title tags updates title" :868, "title update does not URL escape" :881. Nonce application pinned at `test/core/ajax.js:1360`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "makeFragment parse response template title script", limit: 4 });
```
(rank-1 `src.htmx.makeFragment src/htmx.js 603-644`)

## Verdict
Adopt the three-path dispatch and the script duplicate-before-remove pass verbatim — both encode real browser quirks, not style. Adapt the parser choice (`parseHTMLUnsafe` vs DOMParser) to your host's API surface. Omit the legacy root-level-title special case if your server never sends bare `<title>` partials. Coverage caveat: verified against test sources + headless execution of the script/title config flags; no runner executed.
