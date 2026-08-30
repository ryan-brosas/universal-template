<!-- capsule-v2 -->
# FocusGuards shared singleton — how do you guarantee focusin/focusout fire at document edges without thrashing layout per overlay?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How are invisible tab stops injected at body edges so trapped overlays can't lose focus past the last DOM node — and shared across all consumers?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/focus-guards/src/focus-guards.tsx:useFocusGuards` (:24-56), module cache (`guards`, :11-13), count ledger (:7), `<FocusGuards>` wrapper component.
**Signature:** `useFocusGuards(): void` — effect-only hook; guard span: `tabIndex=0, outline:none, opacity:0, position:fixed, pointerEvents:none, data-radix-focus-guard`.
**Data Shape:** module-level `{start, end}` pair created once and REUSED across every mount; integer `count` of active consumers.

### Decisive source
```ts
// Only mutate the DOM when the edge invariant is actually broken. Writing to
// document.body dirties layout and forces a synchronous reflow once sibling
// effects read layout (Popper measuring, react-remove-scroll, aria-hidden,
// FocusScope), so skipping no-op moves avoids that cost on every mount.
if (document.body.firstElementChild !== start) {
  document.body.insertAdjacentElement('afterbegin', start);
}
if (document.body.lastElementChild !== end) {
  document.body.insertAdjacentElement('beforeend', end);
}
count++;
return () => {
  if (count === 1) {
    guards?.start.remove();
    guards?.end.remove();
    guards = null;
  }
  count = Math.max(0, count - 1);
};
```

**Flow:** first consumer creates pair + inserts at body extremes → subsequent overlay mounts reuse cached nodes (only re-inserting when a portal landed AFTER the trailing guard, breaking the last-child invariant) → unmount decrements; ONLY the final consumer removes nodes and nulls the cache. Select content calls useFocusGuards because its portalled content may be the last element in the DOM.
**Invariant:** conditional writes are the performance contract — unconditional insertAdjacentElement forces synchronous reflow under sibling layout readers; the trailing guard must be re-asserted whenever it's no longer lastElementChild (portals append after it).
**Probe:** direct tests `packages/react/focus-guards/src/focus-guards.test.tsx` (128L). Byte-exact anchors: `bash -c "cd /mnt/hdd/utopia/inspo/external/ui-radix-ui && grep -nF 'document.body.firstElementChild !== start' packages/react/focus-guards/src/focus-guards.tsx"` (:33) and `grep -cF 'if (count === 1) {' packages/react/focus-guards/src/focus-guards.tsx"` (=1, :44).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "useFocusGuards guards insertAdjacentElement", limit: 10 });
```

## Verdict
Adopt the singleton+count protocol as-is (tiny, host-free); adapt guard styling only if your reset CSS conflicts; omit nothing. Direct focus-guards.test.tsx coverage upstream at this pin.
