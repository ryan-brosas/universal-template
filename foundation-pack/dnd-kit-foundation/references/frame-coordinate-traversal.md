<!-- capsule-v2 -->
# Frame & iframe traversal — elementFromPoint descent and cross-frame transforms

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How do hit-testing and coordinate math stay correct across iframes, shadow roots, and CSS scale transforms?

## getElementFromPoint + getFrameTransform + scrollable-ancestor walk
**Path/Symbol:** `packages/dom/src/utilities/element/getElementFromPoint.ts:3-29`, `utilities/frame/getFrameTransform.ts` (consumed by PointerSensor :198-204/276-281), `utilities/scroll/getScrollableAncestors.ts:23-90`.
**Signature:** `getElementFromPoint(root: Document|ShadowRoot, {x,y}): Element | null` recurses through IFRAME contentDocuments re-basing coordinates by the frame's rect; `getScrollableAncestors(element, {limit?, excludeElement=true, escapeShadowDOM=true})`.
**Data Shape:** frame transform `{x, y, scaleX, scaleY}`; kernel-space coordinate = `screen * scale + offset`; scrollables returned as insertion-ordered Set (nearest ancestor first).

### Decisive source
```ts
export function getElementFromPoint(root, {x, y}) {
  const element = root.elementFromPoint(x, y);   // works on document AND shadowRoot
  if (isIFrameElement(element)) {
    const {contentDocument} = element;
    if (contentDocument) {
      const {left, top} = element.getBoundingClientRect();
      return getElementFromPoint(contentDocument, {
        x: x - left,
        y: y - top,
      });                                          // descend into the child doc
    }
  }
  return element;
}

// getScrollableAncestors walk
if (escapeShadowDOM && isShadowRoot(node)) return findScrollableAncestors(node.host);
if (scrollParents.has(node)) return scrollParents;              // cycle guard
if (excludeElement && node === element) { /* skip self */ }
else if (isScrollable(node, computedStyle)) scrollParents.add(node);
if (isFixed(node, computedStyle)) { /* fixed ⇒ document.scrollingElement, stop */ }
```

**Flow:** Scroller asks "what is under the pointer" via root-aware elementFromPoint (iframe-descent keeps nested editors working), then walks ancestors collecting scrollables — skipping the element itself by default, escaping shadow roots to the host chain, stopping at fixed elements (their scrollingElement owns the rest), deduping cycles. Sensor coordinates are converted INTO each source's frame space on pointerdown/move so kernels see one consistent space; Feedback divides/multiplies scales when an overlay lives in a DIFFERENT frame than its source (`crossFrame`, Feedback.ts :157-174).
**Invariant:** every raw clientX/Y must pass through `getFrameTransform` before touching operation state (PointerSensor does this at both down and move); the scrollable Set order IS priority for auto-scroll (first match wins); `elementFromPoint` can return null mid-reparent which is why Scroller caches the previous element.
**Probe:** iframe descent live-probed indirectly through sensor suites (no dedicated unit file — DOM coverage caveat); consumers pinned in Feedback/Cursor capsules.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "getFrameTransform", name_pattern: "^getElementFromPoint$", limit: 10 });
```

## Verdict
Adopt root-polymorphic hit-testing + iframe re-based descent + transform-space conversion at sensor boundaries; adapt to your embedding model (portal roots instead of frames); omit fixed-position branch handling only for pages without fixed containers.
