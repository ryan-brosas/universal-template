<!-- capsule-v2 -->
# Trigger dispatch FSM — how does one event listener honor from/once/consume/changed/delay/throttle in a fixed order?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** In what exact order must the trigger modifiers gate a firing, and where do listeners live when `from:` is used?

## addEventListener: the per-event gating pipeline
**Path/Symbol:** `src/htmx.js:addEventListener` (:2496-2602); special trigger kinds in `addTriggerHandler` (:2704-2738); polling loop `processPolling` (:2360-2373); load-once `loadImmediately` (:2648-2661); revealed scan `initScrollHandler`/`maybeReveal` (:2604-2638).
**Signature:** `function addEventListener(elt, handler, nodeData, triggerSpec, explicitCancel)`; internal data fields used: `lastValue` (WeakMap<spec, WeakMap<Node,value>>), `triggeredOnce`, `delayed`, `throttle`, `listenerInfos`.
**Data Shape:** `eltsToListenOn = triggerSpec.from ? querySelectorAllExt(elt, spec.from) : [elt]` — the listener attaches to OTHER elements but `elt` stays the handler's subject. Every registered listener is recorded into `nodeData.listenerInfos` (`{trigger, listener, on}`) so `deInitNode` can remove exactly what it added.

### Decisive source
```js
const eventListener = function(evt) {
  if (!bodyContains(elt)) { eltToListenOn.removeEventListener(triggerSpec.trigger, eventListener); return }
  if (ignoreBoostedAnchorCtrlClick(elt, evt)) { return }
  if (explicitCancel || shouldCancel(evt, eltToListenOn)) { evt.preventDefault() }
  if (maybeFilterEvent(triggerSpec, elt, evt)) { return }
  const eventData = getInternalData(evt)
  eventData.triggerSpec = triggerSpec
  if (eventData.handledFor == null) { eventData.handledFor = [] }
  if (eventData.handledFor.indexOf(elt) < 0) {
    eventData.handledFor.push(elt)
    if (triggerSpec.consume) { evt.stopPropagation() }
    if (triggerSpec.target && evt.target && !matches(asElement(evt.target), triggerSpec.target)) { return }
    if (triggerSpec.once) { if (elementData.triggeredOnce) { return } else { elementData.triggeredOnce = true } }
    if (triggerSpec.changed) {
      const lastValue = elementData.lastValue.get(triggerSpec)
      if (lastValue.has(node) && lastValue.get(node) === value) { return }   // unchanged ⇒ drop
      lastValue.set(node, value)
    }
    if (elementData.delayed) { clearTimeout(elementData.delayed) }
    if (elementData.throttle) { return }
    if (triggerSpec.throttle > 0) {
      if (!elementData.throttle) {
        triggerEvent(elt, 'htmx:trigger'); handler(elt, evt)
        elementData.throttle = getWindow().setTimeout(() => { elementData.throttle = null }, triggerSpec.throttle)
      }
    } else if (triggerSpec.delay > 0) {
      elementData.delayed = getWindow().setTimeout(function() {
        triggerEvent(elt, 'htmx:trigger'); handler(elt, evt)
      }, triggerSpec.delay)
    } else { triggerEvent(elt, 'htmx:trigger'); handler(elt, evt) }
  }
}
```

**Flow:** liveness check on the SUBJECT elt (self-removing listener when it left the DOM) → boosted-ctrl/meta-click pass-through → default prevention (submit-on-form, click-in-submit-button/link rules via `shouldCancel` :2435-2456) → event filter → once → consume → target filter → changed → delay/throttle arbitration → fire.
**Invariant:** ORDER IS SEMANTICS: `consume` stops propagation only after the filter passed and dedup marked this elt as handled; `changed` compares per (spec,node) BEFORE scheduling so a pending delayed call is NOT superseded by an equal-value event — but a NEW value clears `elementData.delayed` first (delay is trailing-reset, throttle is leading-with-lockout; they are mutually exclusive arms). `htmx:trigger` fires immediately before every handler invocation regardless of arm. Polling re-arms itself with setTimeout only after the tick body runs, checks `bodyContains` + `cancelled` each round, and filters events through the same maybeFilterEvent path; status 286 sets that flag (`cancelPolling`). `revealed` uses a 200ms-interval scroll-flag poll (not IntersectionObserver), guarded by `data-hx-revealed`; un-initialized nodes defer the trigger to `htmx:afterProcessNode` once.

**Probe:** Once semantics pinned by `test/attributes/hx-trigger.js` "click once, foo" (:225 block: second identical click adds no request, other event still fires). Delay/throttle tables in "parses spec strings" (:285+). Polling cancel: "polling works" :237 with `xhr.respond(286)` at :252. Changed-value ladder exercised by "input changed once" family. Executed headless: spec parsing for all modifier shapes (see trigger-spec-grammar capsule).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "addEventListener trigger handler once delay throttle", limit: 5 });
```

## Verdict
Adopt the ordering verbatim — reordering any two gates changes observable behavior (e.g. consume-before-filter would swallow sibling listeners). Adapt the window.setTimeout references to your scheduler. Omit the boosted-anchor ctrl-click carve-out if you have no boost feature. Coverage caveat: browser-only gates verified against test sources at pin; runner not executed.
