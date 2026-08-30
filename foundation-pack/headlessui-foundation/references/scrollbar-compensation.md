<!-- capsule-v2 -->
# Scrollbar compensation — how do you avoid layout shift when overflow:hidden removes the scrollbar?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What are the before/after scrollbar-width measurements and why are they taken from DIFFERENT window/documentElement pairs?

## adjustScrollbarPadding ScrollLockStep
**Path/Symbol:** `packages/@headlessui-react/src/hooks/document-overflow/adjust-scrollbar-padding.ts:3-28`.
**Signature:** `adjustScrollbarPadding(): ScrollLockStep` — closure captures `scrollbarWidthBefore`; `before({doc})`, `after({doc, d})`.
**Data Shape:** writes inline `padding-right` on documentElement via shared disposables (auto-restored by SCROLL_ALLOW's d.dispose()).

### Decisive source
```ts
before({ doc }) {
  let documentElement = doc.documentElement
  let ownerWindow = doc.defaultView ?? window
  scrollbarWidthBefore = Math.max(0, ownerWindow.innerWidth - documentElement.clientWidth)
},
after({ doc, d }) {
  let documentElement = doc.documentElement
  // NOTE: This is a bit of a hack, but it's the only way to do this
  let scrollbarWidthAfter = Math.max(0, documentElement.clientWidth - documentElement.offsetWidth)
  let scrollbarWidth = Math.max(0, scrollbarWidthBefore - scrollbarWidthAfter)
  d.style(documentElement, 'paddingRight', `${scrollbarWidth}px`)
}
```

**Flow:** BEFORE any step hides overflow: measure scrollbar as innerWidth − clientWidth (real viewport minus layout viewport). AFTER all steps applied (preventScroll already set overflow:hidden): measure residual gap clientWidth − offsetWidth (what the layout still reserves) and pad right by `before − after`. Net: content column width unchanged when the lock engages.
**Invariant:** the two measurements MUST come from different sources — after-locking, innerWidth no longer reflects a scrollbar; the Math.max guards negative deltas on overlay scrollbars (where widths are 0); padding goes on documentElement because that's whose scrollbar vanished.
**Probe:** deterministic checks executed: max-0 clamps; before/after subtraction semantics. Direct behavior pinned via dialog.test.tsx assertions on documentElement styles while open.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "adjustScrollbarPadding", name_pattern: "^adjustScrollbarPadding$", limit: 5 });
```

## Verdict
Adopt the two-measurement scheme verbatim (it handles classic scrollbars AND overlay scrollbars without UA sniffing); adapt to direction-aware hosts by mirroring for RTL; omit nothing — this is a 25-line step with three documented traps.
