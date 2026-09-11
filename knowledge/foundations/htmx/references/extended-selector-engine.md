<!-- capsule-v2 -->
# Extended selector engine — how do `closest / find / next / previous / global / host` and chevron selectors resolve?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** How must a porter implement htmx's attribute-value selectors (hx-target, hx-indicator, from:, etc.) including the `<tag/>` chevron syntax without breaking comma splitting?

## querySelectorAllExt: prefix keywords + chevron-aware comma split
**Path/Symbol:** `src/htmx.js:querySelectorAllExt` (:1136-1208) with forward/back scans (:1216-1240), single-result `querySelectorExt` (:1247-1253); root resolution `getRootNode(elt, global)` (:443-445).
**Signature:** `function querySelectorAllExt(elt, selector, global)` → `(Node|Window)[]`; `function normalizeSelector(selector)` strips a wrapping `<...>` pair (:1121-1128).
**Data Shape:** Recognized prefixes (checked by `indexOf(... ) === 0` after trimming): `global `, `closest `, `find `, `next`/`nextElementSibling`, `next `, `previous`/`previousElementSibling`, `previous `, plus exact tokens `document`, `window`, `body`, `root`, `host`. Everything unrecognized accumulates and runs as ONE standard selector joined by commas against the resolved root.

### Decisive source
```js
if (selector.indexOf('global ') === 0) { return querySelectorAllExt(elt, selector.slice(7), true) }
...
let chevronsCount = 0; let offset = 0
for (let i = 0; i < selector.length; i++) {
  const char = selector[i]
  if (char === ',' && chevronsCount === 0) { parts.push(selector.substring(offset, i)); offset = i + 1; continue }
  if (char === '<') { chevronsCount++ }
  else if (char === '/' && i < selector.length - 1 && selector[i + 1] === '>') { chevronsCount-- }
}
...
if (selector.indexOf('closest ') === 0) { item = closest(asElement(elt), normalizeSelector(selector.slice(8))) }
else if (selector.indexOf('next ') === 0) { item = scanForwardQuery(elt, normalizeSelector(selector.slice(5)), !!global) }
```

**Flow:** optional `global ` prefix re-dispatches with global=true (escapes the shadow root to the document) → split on top-level commas ONLY: `<` opens and `/>` closes a counter so commas inside chevron selectors don't split → each part: keyword dispatch or accumulate as standard CSS → standard parts query `getRootNode(elt, global)` so scoping follows shadow boundaries.
**Invariant:** `scanForwardQuery` returns the first result that FOLLOWS `start` in document order (`compareDocumentPosition === DOCUMENT_POSITION_PRECEDING`) — NOT the globally first match; backward scan mirrors it. `root` resolves to the subject's shadow root when composed=false. `host` walks out of the shadow root to its custom element. Chevron counting is why `hx-target="previous <div/>"` works while plain-DOM querySelector would reject it; the counter also tolerates multiple chevrons per part. Empty match results are silently dropped (result only pushes truthy items).

**Probe:** Pinned by `test/core/api.js` "should find closest element properly" :38 and "querySelectorExt internal extension api works with just string" :617; shadow-root variants in `test/core/shadowdom.js` "properly retrieves shadow root for extended selector" :58, "properly escapes shadow root for extended selector" :66, "properly retrives shadow root host for extended selector" :74; chevron form exercised at `test/attributes/hx-target.js:174` (`hx-target="previous <div/>"`). Executed headless: `from:(body)` / `from:{p .btn}` combined-selector consumption inside trigger specs shares `consumeCSSSelector` semantics (see trigger-spec-grammar).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "querySelectorAllExt closest find next previous extended selector", limit: 4 });
```
(rank-1 `src.htmx.querySelectorAllExt src/htmx.js 1136-1208`)

## Verdict
Adopt the keyword grammar and the chevron-aware splitter wholesale — it is the contract every attribute value relies on. Adapt `global `/`host` handling to hosts without shadow DOM (they degrade naturally since getRootNode falls back to document). Omit nothing else; even the odd `nextElementSibling` alias is user-visible surface.
