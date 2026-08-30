<!-- capsule-v2 -->
# Node processing & init hash — how does process() re-initialize changed subtrees without double-binding triggers?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** How does htmx decide which nodes need (re)initialization when new content arrives or attributes change, and how is teardown kept symmetric with setup?

## processNode → maybeDeInitAndHash → initNode: content-addressed lifecycle
**Path/Symbol:** `src/htmx.js:processNode` (:3002-3025); `maybeDeInitAndHash` (:2979-2993) over `attributeHash` (:1637-1647)/`stringHash` (:1625-1631, Java-string-hash 32-bit); teardown `deInitNode` (:1666-1680) + `cleanUpElement` (:1685-1690); `initNode` (:2946-2973); candidate selection `findElementsToProcess` (:2794-2816).
**Signature:** `function maybeDeInitAndHash(elt)` → boolean (true ⇒ needs init); `attributeHash(elt)` folds `stringHash(name, stringHash(value, hash))` skipping empty values.
**Data Shape:** Internal data carries `initHash` plus everything teardown must clear: timeout (polling), listenerInfos, onHandlers, queuedRequests... Teardown deletes ALL keys except `firstInitCompleted`.

### Decisive source
```js
function processNode(elt) {
  elt = resolveTarget(elt)
  if (eltIsDisabled(elt)) { cleanUpElement(elt); return }
  const elementsToInit = []
  if (maybeDeInitAndHash(elt)) { elementsToInit.push(elt) }
  forEach(findElementsToProcess(elt), function(child) {
    if (eltIsDisabled(child)) { cleanUpElement(child); return }
    if (maybeDeInitAndHash(child)) { elementsToInit.push(child) }
  })
  forEach(findHxOnWildcardElements(elt), processHxOnWildcard)
  forEach(elementsToInit, initNode)
}

function deInitNode(element) {
  const internalData = getInternalData(element)
  if (internalData.timeout) { clearTimeout(internalData.timeout) }
  forEach(internalData.listenerInfos, info => info.on && removeEventListenerImpl(info.on, info.trigger, info.listener))
  deInitOnHandlers(element)
  forEach(Object.keys(internalData), key => { if (key !== 'firstInitCompleted') delete internalData[key] })
}
```

**Flow:** disabled subtree? clean it and stop → hash the element; changed hash ⇒ de-init then queue for init → query candidates (`VERB_SELECTOR + [hx-boost] a ... + form, [type=submit], [hx-ext], [hx-trigger], + extension.getSelectors()`), same hash gate per child → hx-on wildcard handlers refreshed via XPath scan → batch initNode each survivor.
**Invariant:** The attribute HASH is the idempotence key: re-processing an unchanged subtree is a no-op even though findElementsToProcess matched it ("does not trigger load on re-init of an existing element"); swapping ONE attribute re-inits the node (listeners removed first — no duplicates). Disabled elements are not merely skipped but CLEANED (their handlers/pollers die), matching the security model where `[hx-disable]` freezes behavior. `firstInitCompleted` survives de-init so `trigger:'load'` fires once per element lifetime, not per re-init. cleanUpElement recurses children so removing an ancestor tears down descendants before removal.
**Flow (initNode):** htmx:beforeProcessNode → triggerSpecs + verb processing (or boost / naked-trigger no-op handlers) → button tracking for FORMs and external submit buttons (`form` attribute case) → set firstInitCompleted → afterProcessNode.

**Probe:** Re-init boundary pinned by `test/core/api.js`: "can re-init with new attributes" :405, "does not trigger load on re-init of an existing element" :423. Disable semantics in `test/core/security.js` "can disable a single elt" :11 through dynamic enable/disable family :40-139. hx-on cleanup symmetry: `test/attributes/hx-on-wildcard.js` "de-initializes hx-on-* content properly" :150, "cleans up all handlers when the DOM updates" :222. Executed headless: n/a beyond shared internals battery.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "processNode init hash deinit reinit attributes changed", limit: 4 });
```
(rank-1 `src.htmx.maybeDeInitAndHash src/htmx.js 2979-2993`)

## Verdict
Adopt the hash-gated lifecycle wholesale — it is what makes `htmx.process()` safe to call on every mutation without bookkeeping by callers. Adapt the hash function to any stable fold (keep empty-value exclusion: `foo=""` must equal absent). Omit the extension-selector contribution only if you have no extensions registered.
