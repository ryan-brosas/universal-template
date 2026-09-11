<!-- capsule-v2 -->
# Root-container resolution — which DOM subtrees count as "outside" for a portalled overlay, and how is the main-tree node found?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is resolveContainers' exclusion ladder and the MainTreeProvider hidden-probe fallback?

## useRootContainers / MainTreeProvider / useMainTreeNode
**Path/Symbol:** `packages/@headlessui-react/src/hooks/use-root-containers.tsx:7-63` (resolver), `:90-147` (provider + hook).
**Signature:** `useRootContainers({ defaultContainers?: (Element|Ref)[], portals?: RefObject<Element[]>, mainTreeNode? }): { resolveContainers(): Element[]; contains(el): boolean }`.
**Data Shape:** resolver runs LAZILY per event (useEvent-wrapped) so late-mounted portals are included; candidates are `html > *, body > *` elements.

### Decisive source
```ts
for (let container of ownerDocument?.querySelectorAll('html > *, body > *') ?? []) {
  if (container === document.body) continue            // skip <body>
  if (container === document.head) continue            // skip <head>
  if (!DOM.isElement(container)) continue
  if (container.id === 'headlessui-portal-root') continue   // skip our own portal tree
  if (mainTreeNode) {
    if (container.contains(mainTreeNode)) continue      // skip the MAIN app subtree
    if (container.contains(mainTreeNode?.getRootNode()?.host)) continue  // shadow-root host case
  }
  if (containers.some((d) => container.contains(d))) continue // skip containers we already cover
  containers.push(container)
}
// MainTreeProvider fallback: render a Hidden probe, then adopt the body-child that contains it
{resolvedMainTreeNode === null && (
  <Hidden features={HiddenFeatures.Hidden} ref={(el) => {
    for (let container of getOwnerDocument(el)?.querySelectorAll('html > *, body > *') ?? []) {
      ...
      if (container?.contains(el)) { setMainTreeNode(container); break }
    }
  }} />
)}
```

**Flow:** every outside-click/inert/scroll-lock consumer resolves containers AT EVENT TIME → defaults (dialog panel refs) + registered portals first → then every top-level body child EXCEPT head/body/our-portal-root/the main-tree ancestor and anything already contained → `contains()` answers "is this click inside my world". MainTreeProvider guarantees a mainTreeNode even when the component itself is already portalled, by probing with a temporary Hidden element and adopting its containing body-child.
**Invariant:** resolution is lazy — no stale portal lists; the main-tree exclusion is what lets clicks on the REST of your app close a Popover while clicks inside third-party widgets don't; shadow-DOM hosts are handled by comparing against getRootNode().host.
**Probe:** deterministic checks executed: exclusion order matters only for the containment shortcut; probe-element fallback adopts nearest body child. Direct tests: dialog/popover suites exercising outside-click around portals.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "useRootContainers MainTreeProvider", name_pattern: "^useRootContainers$|^MainTreeProvider$", limit: 5 });
```

## Verdict
Adopt the exclusion ladder verbatim (it IS the definition of "outside" in this library); adapt candidate selection to however your host enumerates top-level roots; omit the Hidden-probe fallback only when you can guarantee a real main-tree marker exists.
