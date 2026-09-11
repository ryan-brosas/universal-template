<!-- capsule-v2 -->
# OOB swap contract — how do `hx-swap-oob` values select targets and swap styles, and what happens with zero matches?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** How must a porter implement out-of-band swaps — value grammar, target selection, template encapsulation, and the no-target error path?

## oobSwap: per-element dispatch driven by the attribute value
**Path/Symbol:** `src/htmx.js:oobSwap` (:1466-1515); fragment sweep `findAndSwapOobElements` (:1856-1870) incl. template unwrap in `swap` (:1937-1942).
**Signature:** `function oobSwap(oobValue, oobElement, settleInfo, rootNode)`; sweep `function findAndSwapOobElements(fragment, settleInfo, rootNode)` → boolean (any found).
**Data Shape:** Attribute grammar for `hx-swap-oob`: `"true"` ⇒ outerHTML into `#<oobElement.id>`; `"style"` ⇒ that style into the id selector; `"style:#selector"` ⇒ style into explicit selector (`indexOf(':') > 0` split at FIRST colon). Nested-OOB policy: elements whose parent is NOT null are skipped-and-stripped unless `config.allowNestedOobSwaps` (default true).

### Decisive source
```js
let selector = '#' + CSS.escape(getRawAttribute(oobElement, 'id'))
let swapStyle = 'outerHTML'
if (oobValue === 'true') { /* keep default */ }
else if (oobValue.indexOf(':') > 0) {
  swapStyle = oobValue.substring(0, oobValue.indexOf(':'))
  selector = oobValue.substring(oobValue.indexOf(':') + 1)
} else { swapStyle = oobValue }
oobElement.removeAttribute('hx-swap-oob'); oobElement.removeAttribute('data-hx-swap-oob')
const targets = querySelectorAllExt(rootNode, selector, false)
if (targets.length) {
  forEach(targets, function(target) {
    const oobElementClone = oobElement.cloneNode(true)
    fragment = getDocument().createDocumentFragment(); fragment.appendChild(oobElementClone)
    if (!isInlineSwap(swapStyle, target)) { fragment = asParentNode(oobElementClone) } // content-of, not the node
    ...
    swapWithStyle(swapStyle, target, target, fragment, settleInfo)
    forEach(settleInfo.elts, elt => triggerEvent(elt, 'htmx:oobAfterSwap', beforeSwapDetails))
  })
  oobElement.parentNode.removeChild(oobElement)
} else {
  oobElement.parentNode.removeChild(oobElement)
  triggerErrorEvent(getDocument().body, 'htmx:oobErrorNoTarget', { content: oobElement, target: selector })
}
```

**Flow:** sweep fragment root + every `<template>` content → strip the attribute BEFORE swapping (prevents re-entry on cloned/inserted nodes) → clone per TARGET (multi-target selectors duplicate the element, one clone each) → inline-vs-content decision via extensions' isInlineSwap (default only outerHTML counts as node-swapping) → htmx:oobBeforeSwap veto (may re-target or set shouldSwap=false) → swap → remove source from fragment.
**Invariant:** Zero matches still REMOVES the element from the fragment and raises `htmx:oobErrorNoTarget` on the BODY with the selector in detail — OOB failure is loud but never aborts the main content swap (the main swap happens after the whole sweep). CSS.escape on the derived `#id` selector supports special-character ids ("handles elements with IDs containing special characters properly"). Template wrappers used ONLY to encapsulate OOB elements are removed afterwards; templates that carry real content survive.

**Probe:** Grammar + multi-target pinned by `test/attributes/hx-swap-oob.js`: "handles outerHTML response properly" :109, "handles innerHTML response properly" :120, "swaps into all targets that match the selector" :165/:178, "oob swap delete works properly" :193, "triggers htmx:oobErrorNoTarget when no targets found" :351, nested-policy pair :131 vs :143, template encapsulation pair :202/:214, table-row configs :227. Executed headless: none needed beyond shared swap-spec battery (S-series) covering style parsing.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "oobSwap out-of-band swap selector", limit: 4 });
```
(rank-1 `src.htmx.oobSwap src/htmx.js 1466-1515`)

## Verdict
Adopt the value grammar and the remove-then-error behavior; both are API-visible. Adapt `isInlineSwap` extension hook if you lack extensions (hardcode outerHTML). Omit shadow-root/global targeting variants only when your host has no shadow DOM (tests :264-351 cover those configurations).
