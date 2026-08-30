<!-- capsule-v2 -->
# Event system & extension onEvent veto — how do events get dispatched twice (camel+kebab) and how can an extension cancel anything?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** What is the return-value contract of triggerEvent, and where exactly do extensions get to veto or observe every htmx event?

## triggerEvent: dispatch → kebab mirror → extension chain
**Path/Symbol:** `src/htmx.js:triggerEvent` (:3102-3126) + `kebabEventName` (:3035-3037) + `makeEvent` (:3044-3048, `composed:true` hack for shadow-DOM global handlers) + error funnel `triggerErrorEvent` (:3055-3057); extension plumbing `withExtensions` (:3078-3086), `getExtensions` (:5030-5057), registry `defineExtension`/`extensionBase` (:4984-5009).
**Signature:** `function triggerEvent(elt, eventName, detail)` → boolean (`false` ⇒ some listener returned false or defaultPrevented); `function getExtensions(elt, extensionsToReturn, extensionsToIgnore)` walks ancestors collecting `hx-ext` names, honoring `ignore:` prefixed entries.
**Data Shape:** detail is ALWAYS an object (`detail == null ⇒ {}`) and gets `.elt` injected. Events are bubbles+cancelable+composed CustomEvents. Logger hook fires before dispatch except for htmx:afterProcessNode.

### Decisive source
```js
let eventResult = elt.dispatchEvent(event)
const kebabName = kebabEventName(eventName)
if (eventResult && kebabName !== eventName) {
  const kebabedEvent = makeEvent(kebabName, event.detail)
  eventResult = eventResult && elt.dispatchEvent(kebabedEvent)
}
withExtensions(asElement(elt), function(extension) {
  eventResult = eventResult && (extension.onEvent(eventName, event) !== false && !event.defaultPrevented)
})
return eventResult
```

**Flow:** logger → error detail ⇒ console.error + nested `htmx:error` → DOM dispatch of camelCase name → if not cancelled and the kebab rendering DIFFERS, dispatch again with the SAME detail object → each element-scoped extension's `onEvent(name, evt)` may return false (or call preventDefault) to cancel; result is the conjunction.
**Invariant:** The double-dispatch exists so `htmx:configRequest` and `htmx:config-request` listeners BOTH work, while identical renderings fire ONCE ("events are only dispatched once if kebab and camel case match"). Returning false from a listener prevents default AND becomes the veto signal consumed by every gate in the request/swap pipelines. Extensions are resolved PER ELEMENT at call time (ancestor hx-ext walk, ignore-list accumulates down the tree), never cached — dynamic defineExtension/removeExtension take effect immediately. withExtensions swallows extension THROWS into logError so one bad extension cannot kill the pipeline.
**Flow (registry):** defineExtension merges over extensionBase defaults (init runs immediately with internalAPI; getSelectors feeds findElementsToProcess) — partial extension objects are legal.

**Probe:** Kebab semantics pinned by `test/core/events.js`: "htmx:configRequest is also dispatched in kebab-case" :48, "events are only dispatched once if kebab and camel case match" :67. Extension veto: `test/core/extensions.js` "should support event cancellation by returning false" :11, preventDefault variant :27, "withExtensions catches and logs any exceptions" :43, encodeParameters hook :58, "extensionBase return expected values" :77. Swap-side extension integration: `test/core/extension-swap.js` :34/:44.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "triggerEvent kebab event dispatch extension onEvent", limit: 4 });
```
(rank-1 `src.htmx.triggerEvent src/htmx.js 3102-3126`)

## Verdict
Adopt the veto-by-false contract and the same-detail double-dispatch. Adapt kebabization only to preserve exact one-dispatch-when-equal behavior. Omit composed:true ONLY if you drop shadow-DOM support — it is documented as a deliberate encapsulation break.
