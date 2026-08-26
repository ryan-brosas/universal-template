<!-- capsule-v2 -->
# hx-on wildcard handlers — how do inline event attributes get names, eval gating, and symmetric teardown?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** How are `hx-on:*`/`hx-on-*` attributes converted into listeners, which shorthand prefixes map to `htmx:` events, and why must re-processing wipe old handlers first?

## processHxOnWildcard: attribute-name grammar + lazy Function compilation
**Path/Symbol:** `src/htmx.js:processHxOnWildcard` (:2916-2941) + `addHxOnEventHandler` (:2891-2911); candidate discovery `findHxOnWildcardElements` (:2777-2788) over the compiled XPath `HX_ON_QUERY` (:2764-2766) + `shouldProcessHxOn` (:2744-2758).
**Signature:** `function processHxOnWildcard(elt)`; name grammar: after `'hx-on'`/`'data-hx-on'`, next char MUST be `-` or `:`; remainder is the event name with rewrites: leading `:` ⇒ `htmx<name>`; leading `-` ⇒ `htmx:<rest>`; leading `htmx-` ⇒ `htmx:<rest>`.
**Data Shape:** Handler body string compiled lazily via `new Function('event', code)` on FIRST invocation, memoized in the closure (`func`); every listener recorded in `nodeData.onHandlers`.

### Decisive source
```js
const listener = function(e) {
  maybeEval(elt, function() {              // gated by config.allowEval
    if (eltIsDisabled(elt)) { return }
    if (!func) { func = new Function('event', code) }
    func.call(elt, e)
  })
}
elt.addEventListener(eventName, listener)
nodeData.onHandlers.push({ event: eventName, listener })
...
function processHxOnWildcard(elt) {
  // wipe any previous on handlers so that this function takes precedence
  deInitOnHandlers(elt)
  for (let i = 0; i < elt.attributes.length; i++) { ... addHxOnEventHandler(elt, eventName, value) }
}
```

**Flow:** processNode scans subtree with an XPath matching any attribute whose name starts with hx-on:/data-hx-on:/hx-on-/data-hx-on- (DocumentFragment children handled separately) → per element: de-init previous wildcard handlers → register one listener per qualifying attribute.
**Invariant:** The WIPE-FIRST step makes attribute edits idempotent under process() (test "cleans up all handlers when the DOM updates"). Lazy compilation means a syntax error in a handler body only throws at first event, inside maybeEval's error surface (`htmx:evalDisallowedError` when allowEval=false — pinned by its own test). The three rewrite forms all normalize onto the `htmx:` namespace so inline handlers can observe internal lifecycle events (`::shorthand expands into htmx:`). Disabled-element check happens INSIDE the handler, so freezing a subtree mid-session stops handlers without re-processing.
**Flow (discovery):** XPath runs against the element OR fragment children; results are pushed as Elements and processed even when the node itself carries no other htmx behavior — this is why hx-on works standalone.

**Probe:** `test/attributes/hx-on-wildcard.js`: basic events :11, dashes-not-colons :18, `::` shorthand :47, `--` shorthand :58, data-hx-on form :79, `this` symbol binding :90, multi-line JSON bodies :102/:116, load/revealed firing :136/:143, teardown pair :150/:222, allowEval suppression :176. Security-side disable ladder in `test/core/security.js` :173-201 ("can disable hx-on ... dynamically").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "hx-on wildcard event handler name htmx prefix", limit: 4 });
```
(rank-1 `src.htmx.addHxOnEventHandler src/htmx.js 2891-2911`)

## Verdict
Adopt the name grammar, lazy compile, and wipe-first re-registration. Adapt `new Function` to your sandbox policy (CSP hosts must keep allowEval=false and accept the no-op). Omit the DocumentFragment branch only if you never process fragments directly.
