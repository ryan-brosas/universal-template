<!-- capsule-v2 -->
# Polling & revealed/intersect scheduling — how do periodic and visibility triggers avoid leaks?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** How are `every`, `revealed`, and `intersect` triggers scheduled, cancelled, and de-duplicated across scroll events?

## processPolling / initScrollHandler / addTriggerHandler(intersect)
**Path/Symbol:** `src/htmx.js:processPolling` (:2360-2373) storing its timeout in `nodeData.timeout`; shared scroll poller `initScrollHandler` (:2606-2622) with module-level `windowIsScrolling` latch + 200ms setInterval; `maybeReveal` (:2627-2638); intersect branch in `addTriggerHandler` (:2709-2727).
**Signature:** polling tick: re-arm via setTimeout ONLY inside the guard `bodyContains(elt) && nodeData.cancelled !== true`; each round synthesizes `hx:poll:trigger` through the SAME event-filter pipeline as user events.
**Data Shape:** intersect options: `root` (selector resolved via querySelectorExt), `threshold` (parseFloat of the spec string). Observer fires `intersect` as a NORMAL event on the element, which the registered trigger listener then processes — one code path for filtering/dedup.
**Data Shape:** reveal scan selector is ATTRIBUTE-SUBSTRING based: `[hx-trigger*='revealed'],[data-hx-trigger*='revealed']` — cheap but means the word 'revealed' anywhere in hx-trigger enrolls the element.

### Decisive source
```js
function processPolling(elt, handler, spec) {
  const nodeData = getInternalData(elt)
  nodeData.timeout = getWindow().setTimeout(function() {
    if (bodyContains(elt) && nodeData.cancelled !== true) {
      if (!maybeFilterEvent(spec, elt, makeEvent('hx:poll:trigger', { triggerSpec: spec, target: elt }))) {
        handler(elt)
      }
      processPolling(elt, handler, spec)   // self re-arm AFTER the tick body
    }
  }, spec.pollInterval)
}
...
setInterval(function() {
  if (windowIsScrolling) {
    windowIsScrolling = false
    forEach(getDocument().querySelectorAll("[hx-trigger*='revealed'],[data-hx-trigger*='revealed']"), maybeReveal)
  }
}, 200)
```

**Flow:** every ⇒ setTimeout chain; revealed ⇒ scroll-flag latch drained at ≤5Hz checking `isScrolledIntoView` (top < innerHeight && bottom >= 0) guarded by a `data-hx-revealed` attribute; intersect ⇒ IntersectionObserver emitting synthetic events.
**Invariant:** Cancellation is cooperative: status-286 responses set `cancelled` via cancelPolling; element removal stops the chain at the next tick (bodyContains false) even before deInitNode's clearTimeout. The scroll handler is created ONCE globally (null-guard) regardless of how many revealed elements exist, and the flag-latch coalesces bursts of scroll events into one query sweep. Reveal-before-init defers the trigger to afterProcessNode so requests never fire from unprocessed nodes.
**Flow:** because polling goes through maybeFilterEvent, `[trigger='every 2s[someCondition]']` filters ticks exactly like user events.

**Probe:** "polling works" (`test/attributes/hx-trigger.js:237`) drives >5 rapid polls then responds 286 to prove cancellation; interval parsing table :285+ includes `every 0s`/`every 0ms` ⇒ pollInterval 0. Reveal semantics pinned by hx-on-wildcard tests "should fire when triggered by revealed" :143 and load-gate :136. Executed headless: n/a (timer/observer semantics).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "processPolling every interval revealed scroll intersect observer", limit: 5 });
```
(companion rank-1: getTriggerSpecs family)

## Verdict
Adopt the self-rearming timeout with bodyContains/cancelled guards and the single global scroll latch. Adapt IntersectionObserver usage directly (the emit-normal-event indirection is what lets once/consume apply to visibility too — keep it). Omit the substring-enrollment caveat at your peril: renaming the trigger silently breaks reveal scanning.
