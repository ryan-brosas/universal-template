<!-- capsule-v2 -->
# Indicators, disabled elts & class hygiene — how are request-state classes refcounted and why does empty-class removal matter?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** How do hx-indicator/hx-disabled-elt resolve to possibly-shared elements, and what bookkeeping prevents one request's completion from stripping another's spinner?

## addRequestIndicatorClasses / disableElements / removeRequestIndicators: requestCount refcount
**Path/Symbol:** `src/htmx.js:addRequestIndicatorClasses` (:3371-3382) + `disableElements` (:3388-3402) + paired removal (:3408-3426); target resolution via findAttributeTargets (:1354-1379) incl. `inherit` keyword expansion; injected CSS `insertIndicatorStyles` (:5084-5096); class-attribute cleanup in removeClassFromElement (:1032-1051); history-side mirror cleanInnerHtmlForHistory (:3237-3248).
**Signature:** indicators = `findAttributeTargets(elt,'hx-indicator') || [elt]`; disabled = `findAttributeTargets(elt,'hx-disabled-elt')`; each hit gets `internalData.requestCount = (requestCount||0)+1`; on completion decrement and only at ZERO remove the class / the disabled attribute (only when `data-disabled-by-htmx` is present).
**Data Shape:** `findAttributeTargets` special values: `'this'` ⇒ the element bearing the attribute (`findThisElement`); selector returning EMPTY ⇒ logError + DUMMY_ELT sentinel (never null-crash); value containing whole-word `inherit` (regex `/(^|,)(\s*)inherit(\s*)($|,)/`) recursively appends the nearest ancestor-with-attribute's own targets.

### Decisive source
```js
function removeRequestIndicators(indicators, disabled) {
  forEach(indicators.concat(disabled), ele => { getInternalData(ele).requestCount = (getInternalData(ele).requestCount || 1) - 1 })
  forEach(indicators, ic => { if (getInternalData(ic).requestCount === 0) removeClassFromElement(ic, htmx.config.requestClass) })
  forEach(disabled, d => {
    if (getInternalData(d).requestCount === 0 && d.hasAttribute('data-disabled-by-htmx')) {
      d.removeAttribute('disabled'); d.removeAttribute('data-disabled-by-htmx')
    }
  })
}
```

**Flow:** attach happens AFTER the beforeRequest veto (so cancelled requests never flash spinners); detach runs in onload/onerror/onabort/ontimeout arms — but HX-Redirect/HX-Refresh set `responseInfo.keepIndicators=true` so navigation keeps them visible. The injected stylesheet hides `.htmx-indicator` unless inside `.htmx-request` (descendant or self), with a 200ms ease-in.
**Invariant:** The refcount lives on the TARGET element's internal data, not the requesting element — two concurrent requests sharing an indicator each increment. `removeClassFromElement` removes the whole `class` ATTRIBUTE when empty (class-cleanup tests) which keeps DOM diffs clean; history snapshots strip BOTH the request class and htmx-added disabled attributes so restored pages don't look mid-flight. Disabled elements are tagged `data-disabled-by-htmx` so pre-existing native disabled states are never un-set by htmx.

**Probe:** Refcount pin: `test/attributes/hx-indicator.js` "multiple requests with same indicator are handled properly" :97; target syntaxes: no-indicator default :11, explicit :20, relative :35, data-prefix :47, `closest ` :62, `this` :85, initiator-removed :74; inherit keyword trio :127/:145/:168 ("inherit chain breaks properly"). Class hygiene: `test/core/class-cleanup.js` :11/:26/:40/:54. History mirror: hx-push-url.js "history restore should not have htmx support classes in content" :84 + "history cache clears out disabled attribute" :292.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "hx-indicator request class disabled element refcount", limit: 5 });
```
(companion: findAttributeTargets resolves rank-1 for query "findAttributeTargets inherit this dummy selector")

## Verdict
Adopt the refcount + ownership-tag design exactly; both prevent classic double-spinner and stuck-disabled bugs. Adapt indicator CSS injection (respect CSP nonces as source does with inlineStyleNonce). Omit the inherit-keyword expansion only if you also drop it from every other attribute consumer — it is implemented once in findAttributeTargets for all callers.
