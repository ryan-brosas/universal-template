<!-- capsule-v2 -->
# Config & boot sequence — how does the runtime initialize once, merge meta-config, and expose its public API surface?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** In what order does htmx bootstrap, which knobs exist at each layer, and what is the internalAPI contract handed to extensions?

## ready() → metaConfig → indicator styles → processNode → popstate takeover
**Path/Symbol:** `src/htmx.js` IIFE close (:5115-5156); `ready` (:5074-5082, isReady flag + readyState failsafe because DOMContentLoaded→readystate has a gap); `getMetaConfig`/`mergeMetaConfig` (:5098-5113); config defaults block (:77-289); public-API rebind ladder (:302-322); internalAPI export (:324-352); responseHandling defaults (:264-268).
**Signature:** `htmx.config` is a plain mutable object; `<meta name="htmx-config" content='{...JSON...}'>` merges ONCE at boot over defaults. Public functions are declared `null` then REASSIGNED after definition ("Tsc madness" — declaration order, not decoration).
**Data Shape:** Notable defaults a porter must copy: defaultSwapDelay 0 / defaultSettleDelay 20; methodsThatUseUrlParams `['get','delete']`; selfRequestsOnly TRUE; historyRestoreAsHxRequest true; allowNestedOobSwaps true; scrollBehavior 'instant'; triggerSpecsCache null (opt-in); attributesToSettle `['class','style','width','height']`; disableSelector `'[hx-disable], [data-hx-disable]'`.

### Decisive source
```js
ready(function() {
  mergeMetaConfig()
  insertIndicatorStyles()
  let body = getDocument().body
  processNode(body)
  const restoredElts = getDocument().querySelectorAll("[hx-trigger='restored'],[data-hx-trigger='restored']")
  body.addEventListener('htmx:abort', function(evt) {
    const target = evt.detail.elt || evt.target
    const internalData = getInternalData(target)
    if (internalData && internalData.xhr) { internalData.xhr.abort() }
  })
  const originalPopstate = window.onpopstate ? window.onpopstate.bind(window) : null
  window.onpopstate = function(event) {
    if (event.state && event.state.htmx) { restoreHistory(); forEach(restoredElts, elt => triggerEvent(elt,'htmx:restored',...)) }
    else if (originalPopstate) { originalPopstate(event) }
  }
  getWindow().setTimeout(function(){ triggerEvent(body,'htmx:load',{}); body = null /* kill reference for gc */ }, 0)
})
```

**Flow:** meta-config BEFORE processing so attribute semantics see final config → style injection before first swap → initial processNode(body) → abort delegation on body (htmx:abort detail.elt or target) → popstate chain-preservation → deferred initial htmx:load so onLoad handlers registered during parse still catch it.
**Invariant:** internalAPI (handed to extension init) exposes ~25 internals incl. getInternalData, swap, makeSettleInfo, oobSwap, getTriggerSpecs, withExtensions — extensions are FIRST-CLASS consumers, not plugin-callback secondaries. The single global abort listener means ANY element can cancel another's in-flight xhr by dispatching htmx:abort AT it. Version string lives at `htmx.version` ('2.0.10' at pin).
**Flow:** `htmx.location` is an indirection point (proxy of window.location) — tests and embedders stub redirects through it.

**Probe:** Boot-order pins: `test/core/internals.js` "without meta config getMetaConfig returns null" :212; "internalAPI settleImmediately completes settle tasks" :217. Popstate chain: internals :166/:184. Abort delegation exercised by hx-sync programmatic-abort test (`test/attributes/hx-sync.js:195`). Config knob matrix: `test/core/config.js` whole file (responseHandling family :12-288). Executed headless: kernel loads under minimal shim exposing only document/window/listener elements — evidence that the boot path needs no framework.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "ready metaConfig insertIndicatorStyles processNode onpopstate", limit: 5 });
```
(companion rank-1: saveToHistoryCache for history wiring queries)

## Verdict
Adopt the ordering (config → styles → process → listeners) as a unit. Adapt the API-rebind pattern to normal hoisting in non-TS hosts. Omit the meta-config reader if your host injects config programmatically — but keep merge-once semantics.
