<!-- capsule-v2 -->
# Swap pipeline & settle tasks — how does swap() order OOB, select, preserve, focus, title, and settling?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** What is the exact choreography inside a swap — before, during, and across the settle delay — that a porter must reproduce for correct event timing?

## swap(): the doSwap/doSettle sandwich with view-transition wrapping
**Path/Symbol:** `src/htmx.js:swap` (:1880-2059); style dispatch `swapWithStyle` (:1799-1849) + per-style fns (:1697-1790); insertion core `insertNodesBefore` (:1606-1616); attribute merge `handleAttributes`/`cloneAttributes` (:1559-1574, :1426-1437); load tasks `makeAjaxLoadTask` (:1580-1587); focus `processFocus` (:1592-1598).
**Signature:** `function swap(target, content, swapSpec, swapOptions)`; swapSpec `{swapStyle, swapDelay, settleDelay, transition?, ignoreTitle?, scroll?, show?, focusScroll?}`; settleInfo `{tasks: Function[], elts: Element[], title?}`.
**Data Shape:** Every inserted node gets `config.addedClass`, and each non-text/comment child schedules a task: remove addedClass → processNode → processFocus → fire htmx:load. Attribute merging snapshots new-node attributes then queues a SETTLE-TIME clone-back so transient classes (htmx-request etc.) don't leak into settled content.

### Decisive source
```js
// normal swap
if (swapOptions.select) { /* re-fragment to matching nodes only */ }
handlePreservedElements(fragment)
swapWithStyle(swapSpec.swapStyle, swapOptions.contextElement, target, fragment, settleInfo)
restorePreservedElements()
...
forEach(settleInfo.elts, elt => { addClassToElement(elt, htmx.config.settlingClass); triggerEvent(elt,'htmx:afterSwap', ...) })
maybeCall(swapOptions.afterSwapCallback)
if (!swapSpec.ignoreTitle) { handleTitle(settleInfo.title) }
const doSettle = function() {
  forEach(settleInfo.tasks, task => task.call())
  ...removeClassFromElement(elt, htmx.config.settlingClass); triggerEvent(elt,'htmx:afterSettle',...)
  if (swapOptions.anchor) {...scrollIntoView}
  updateScrollState(settleInfo.elts, swapSpec)
  maybeCall(swapOptions.afterSettleCallback); maybeCall(settleResolve)
}
if (swapSpec.settleDelay > 0) getWindow().setTimeout(doSettle, swapSpec.settleDelay) else doSettle()
```

**Flow (doSwap):** resolve target → rootNode from contextElement → capture activeElement + selection range → makeFragment → title precedence (swapOptions.title over fragment.title) → historyRequest narrows fragment to `[hx-history-elt]` → selectOOB list → findAndSwapOobElements (+ template-wrapped OOB, empty templates removed after use) → hx-select re-fragmentation → preserve pantry → style dispatch → restore pantry → focus/selection restore by id when the original left the DOM (`preventScroll = !focusScroll`) → swapping-class removal → afterSwap events → title merge → delayed settle.
**Invariant:** swapWithStyle falls through unknown styles to EXTENSIONS first (`ext.handleSwap` returning truthy short-circuits, arrays of returned elements get their own ajax-load tasks), then `'innerHTML'`, else RECURSES on `config.defaultSwapStyle` — an extension can claim ANY style name including custom ones. outerHTML on BODY silently degrades to innerHTML (fragments cannot hold `<body>`). Settle is not cosmetic: attribute clone-BACK tasks run there, so removing the delay changes observable class/attribute behavior.
**Invariant (view transitions):** with `transition:true` (or globalViewTransitions) doSwap wraps itself in `document.startViewTransition` and the settle promise RESOLVES the transition — settle completion gates the visual transition.

**Probe:** Style table pinned by `test/attributes/hx-swap.js` "properly parses various swap specifications" :241 (30+ assertions incl. modifier-only strings keeping innerHTML default and nonsense words tolerated between modifiers); body-fallback "swap outerHTML on body falls back to innerHTML properly" :86; textContent path ignores OOB :47; delay arms :291/:303/:329/:341; scroll/show family :359-454 incl. `show:window:bottom` :439; error surface "swapError fires if swap throws exception" :541; focus restore via regressions "can trigger swaps from fields that don't support setSelectionRange" :183. Executed headless: getSwapSpecification defaults/multi-modifier shapes (S1-S4 battery).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "swapWithStyle swap style outerHTML innerHTML delete none extension handleSwap", limit: 4 });
```
(rank-1 `src.htmx.swapWithStyle src/htmx.js 1799-1849`; companion `swap` resolves rank-1 for query "swap function doSwap settleResolve startViewTransition" at 1880-2059)

## Verdict
Adopt the choreography order verbatim — every event-timing bug report about htmx reduces to reordering here. Adapt the settle-delay default (20ms) and view-transition wrapping to host capabilities. Omit the anchor-scroll tail only if your host never passes anchors through requests.
