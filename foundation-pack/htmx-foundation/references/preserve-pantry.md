<!-- capsule-v2 -->
# hx-preserve pantry — how do preserved elements survive a swap without losing state?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** How does htmx keep a live DOM node (video, iframe, canvas state) across an outerHTML swap that would otherwise destroy and recreate it?

## handlePreservedElements / restorePreservedElements: pantry parking via moveBefore
**Path/Symbol:** `src/htmx.js:handlePreservedElements` (:1533-1552) + `restorePreservedElements` (:1517-1528); invoked around every style dispatch in `swap` (:1952-1954) and per-target inside `oobSwap` (:1500-1502).
**Signature:** `function handlePreservedElements(fragment)`; `function restorePreservedElements()`; pantry id literal `#--htmx-preserve-pantry--`.
**Data Shape:** Preserved candidates: fragment nodes matching `[hx-preserve], [data-hx-preserve]`. If the live document has an element with the SAME id, the live one is moved out (pantry) or substituted in place (fallback path). The pantry div is created after `<body>` (`insertAdjacentHTML('afterend', ...)`) on first use and removed when drained.

### Decisive source
```js
forEach(findAll(fragment, '[hx-preserve], [data-hx-preserve]'), function(preservedElt) {
  const id = getAttributeValue(preservedElt, 'id')
  const existingElement = getDocument().getElementById(id)
  if (existingElement != null) {
    if (preservedElt.moveBefore) {          // modern path: MOVE the live element (state-preserving)
      let pantry = find('#--htmx-preserve-pantry--')
      if (pantry == null) { getDocument().body.insertAdjacentHTML('afterend', "<div id='--htmx-preserve-pantry--'></div>"); pantry = find(...) }
      pantry.moveBefore(existingElement, null)
    } else {
      preservedElt.parentNode.replaceChild(existingElement, preservedElt) // legacy: swap in place
    }
  }
})
// restore:
for (const preservedElt of [...pantry.children]) {
  const existingElement = find('#' + preservedElt.id)
  existingElement.parentNode.moveBefore(preservedElt, existingElement)
  existingElement.remove()
}
```

**Flow:** before style dispatch: park live twins → swap proceeds (the fragment copy takes the slot) → after: moveBefore each parked node back into its new twin's position and DELETE the twin.
**Invariant:** `moveBefore` is the whole point — unlike appendChild/insertBefore it does NOT reset iframe/video playback, focus, or canvas state. Two paths exist because `moveBefore` is recent: the fallback REPLACES the incoming fragment node with the live element directly (no pantry round-trip; pinned by test "when moveBefore is disabled/missing preserved content is copied into fragment instead of pantry"). Elements with no live twin pass through untouched ("handles preserved element that might not be existing"). Preserve interacts correctly with hx-select and OOB exclusions (tests :29/:38/:49).
**Flow (restore ordering):** restorePreservedElements runs immediately AFTER swapWithStyle but BEFORE settle tasks — settle-time attribute merge-back therefore operates on the restored (live) nodes.

**Probe:** `test/attributes/hx-preserve.js`: "handles basic response properly" :11, missing-twin :20, hx-select exclusion :29, oob exclusion :38, select-oob :49, relocation across oob targets :60, no-moveBefore fallback :72. Executed headless: n/a (DOM-move semantics are browser-boundary behavior); expectations transcribed from the named tests at pin.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "hx-preserve preserved elements pantry", limit: 4 });
```
(rank-1 `src.htmx.restorePreservedElements src/htmx.js 1517-1528`, rank-2 handlePreservedElements 1533-1552)

## Verdict
Adopt the two-path design and the exact pantry id/creation/drain lifecycle. Adapt the parking location if your host forbids body-sibling elements (any detached-but-referenced container works). Omit nothing: dropping the fallback breaks every pre-moveBefore browser, dropping the pantry changes focus restoration semantics.
