<!-- capsule-v2 -->
# Inert-others refcount — how do you freeze the whole page except your component without breaking nested overlays?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** Which elements get `inert`/`aria-hidden`, and how are original attribute values restored when two overlays mark the same node?

## useInertOthers / markInert / markNotInert
**Path/Symbol:** `packages/@headlessui-react/src/hooks/use-inert-others.tsx:6-125`.
**Signature:** `useInertOthers(enabled: boolean, { allowed?: () => (HTMLElement|null)[]; disallowed?: () => (HTMLElement|null)[] } = {}): void` (module-level `originals: Map<HTMLElement, {aria-hidden, inert}>`, `counts: Map<HTMLElement, number>`).
**Data Shape:** cleanup functions returned by markInert are registered in one disposables group disposed on effect teardown; restoration writes back the EXACT pre-existing attribute value or removes the attribute if it was absent.

### Decisive source
```ts
function markInert(element) {
  let count = counts.get(element) ?? 0
  counts.set(element, count + 1)
  if (count !== 0) return () => markNotInert(element)   // already inert: NO second write
  originals.set(element, { 'aria-hidden': element.getAttribute('aria-hidden'), inert: element.inert })
  element.setAttribute('aria-hidden', 'true')
  element.inert = true
  return () => markNotInert(element)
}
function markNotInert(element) {
  let count = counts.get(element) ?? 1
  if (count === 1) counts.delete(element); else counts.set(element, count - 1)
  if (count !== 1) return                                // not the last owner: keep inert
  let original = originals.get(element)
  if (original['aria-hidden'] === null) element.removeAttribute('aria-hidden')
  else element.setAttribute('aria-hidden', original['aria-hidden'])
  element.inert = original.inert
}
// sibling crawl:
let parent = element.parentElement
while (parent && parent !== ownerDocument.body) {
  for (let node of parent.children) {
    if (allowedElements.some((el) => node.contains(el))) continue   // never inert an ancestor of an allowed el
    d.add(markInert(node))
  }
  parent = parent.parentElement
}
```

**Flow:** enabled+top-layer → mark every `disallowed()` element → for each allowed element walk parents up to `<body>` marking all siblings inert unless the sibling CONTAINS another allowed element → dispose restores everything in reverse. The docstring example shows header/footer inert while `<main>` stays interactive because it's a parent of the allowed listbox.
**Invariant:** first marker snapshots ORIGINAL values; later markers only bump the counter — so overlapping Dialogs can't clobber each other's restore state (live probe: attr restored to pre-existing value only after BOTH releases). The allowed-check uses `node.contains(el)` per sibling, which is what keeps the path from allowed element to body permanently interactive.
**Probe:** live `/tmp/hui-pass1-probe/probe-stack-inert-overflow.mjs` pins double-mark/single-release-still-inert/final-restore-to-original. Direct test: `packages/@headlessui-react/src/hooks/use-inert-others.test.tsx:12-181` ('should be possible to inert an element', 'should mark the element as not inert anymore once all references are gone', 'mark everything but allowed containers').
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "useInertOthers", name_pattern: "^useInertOthers$", limit: 5 });
```

## Verdict
Adopt the refcount ladder and contains-guard verbatim; adapt "allowed/disallowed resolvers" to whatever produces your overlay roots (Dialog passes its closest `[data-headlessui-portal]`); omit the disallowed main-tree special case if your host has no portalled main tree. `element.inert` requires the platform invariant — provide a polyfill shim on older engines.
