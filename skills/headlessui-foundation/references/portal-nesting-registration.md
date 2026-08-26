<!-- capsule-v2 -->
# Portal nesting registration — how do child Popover panels inside a Dialog's portal stay "inside" for outside-click and inert?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the portal-root reuse rule, the data-headlessui-portal wrapper contract, and the recursive useNestedPortals registration?

## Portal / PortalGroup / useNestedPortals / PortalParentContext
**Path/Symbol:** `packages/@headlessui-react/src/components/portal/portal.tsx:28-64` (`usePortalTarget`), `:101-135` (unmount cleanup + wrapper div), `:202-237` (`useNestedPortals`).
**Signature:** `useNestedPortals(): [RefObject<HTMLElement[]>, FC]`; `PortalGroup({ target: RefObject<HTMLElement|null> })`; `Portal({ enabled = true, ownerDocument? })`.
**Data Shape:** shared root `div#headlessui-portal-root` appended to body once per document; every Portal wraps content in `<div data-headlessui-portal="">`.

### Decisive source
```ts
// target resolution: group context wins, else shared #headlessui-portal-root
let existingRoot = ownerDocument?.getElementById('headlessui-portal-root')
if (existingRoot) return existingRoot
let root = ownerDocument.createElement('div')
root.setAttribute('id', 'headlessui-portal-root')
return ownerDocument.body.appendChild(root)

// self-cleanup when the LAST portal unmounts:
useOnUnmount(() => {
  if (!target) return
  if (target.childNodes.length <= 0) target.parentElement?.removeChild(target)
})

// recursive registration: children register with parent too
let register = useEvent((portal) => { portals.current.push(portal); if (parent) parent.register(portal)
                                       return () => unregister(portal) })
// render wrapper registers itself + wires disposables:
ref={(el) => { d.dispose(); if (parent && el) d.add(parent.register(el)) }}
```

**Flow:** Dialog renders under ForcePortalRoot(true) so its content lands in the shared body-level root → each nested component (Popover panel etc.) creates its own `[data-headlessui-portal]` wrapper INSIDE that tree and registers it upward through PortalParentContext → Dialog's resolveRootContainers includes portals.current, making outside-click/inert/scroll-lock treat nested panels as INSIDE. The iOS touchmove crawl also stops at this exact attribute.
**Invariant:** registration is RECURSIVE (a grandchild portal appears in the top Dialog's list because register bubbles); unmount cleanup removes the shared root only when EMPTY; `enabled=false` renders in place (no portal). PortalGroup redirects the target to a specific element (e.g. dialog panel) instead of the shared root.
**Probe:** direct tests: `packages/@headlessui-react/src/components/portal/portal.test.tsx` pins nesting + cleanup behavior. Deterministic check: cleanup condition is childNodes.length <= 0 on the GROUP TARGET, not the wrapper.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "useNestedPortals PortalParentContext", limit: 5 });
```

## Verdict
Adopt the shared-root + wrapper-attribute + recursive-registration triad verbatim — dropping any one breaks outside-click containment or iOS scroll rules downstream; adapt naming of the dataset attribute to your brand but keep ONE canonical marker; omit ownerDocument plumbing only for single-document hosts.
