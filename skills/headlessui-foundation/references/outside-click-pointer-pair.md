<!-- capsule-v2 -->
# Outside-click pointer pair — why judge the pointerdown target and how do touch scrolling and iframes avoid false closes?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What exact event choreography decides "the user clicked outside" without misfiring on drag-scrolls, stopPropagation layers, or iframe focus?

## useOutsideClick
**Path/Symbol:** `packages/@headlessui-react/src/hooks/use-outside-click.ts:19-198` (`MOVE_THRESHOLD_PX`, `useOutsideClick`).
**Signature:** `useOutsideClick(enabled: boolean, containers: ContainerInput | (() => ContainerInput), cb: (event, target: HTMLOrSVGElement & Element) => void): void`.
**Data Shape:** containers resolve recursively through functions/arrays/Sets; every listener registers in CAPTURE phase (`true` last arg).

### Decisive source
```ts
const MOVE_THRESHOLD_PX = 30

// mouse/pen path: remember WHERE the press started...
useDocumentEvent(enabled, 'pointerdown', (event) => {
  if (isMobile()) return
  initialClickTarget.current = (event.composedPath?.()?.[0] || event.target)
}, true)
// ...and judge THAT target on release
useDocumentEvent(enabled, 'pointerup', (event) => {
  if (!initialClickTarget.current) return
  let target = initialClickTarget.current
  initialClickTarget.current = null
  return handleOutsideClick(event, () => target)
}, true /* capture: Menu-in-DialogPanel stopPropagation must NOT cancel this */)

// touch path: cancel when the finger moved >= 30px (scrolling, not clicking)
if (Math.abs(end.x - start.x) >= MOVE_THRESHOLD_PX || Math.abs(end.y - start.y) >= MOVE_THRESHOLD_PX) return
return handleOutsideClick(event, () => DOM.isHTMLorSVGElement(event.target) ? event.target : null)

// iframe path: window blur where activeElement is a child iframe == outside click
useWindowEvent(enabled, 'blur', (event) => handleOutsideClick(event, () =>
  DOM.isHTMLIframeElement(window.document.activeElement) ? window.document.activeElement : null), true)
```

**Flow:** handler ladder — bail on `event.defaultPrevented` (nested components veto by preventing default) → resolve+validate target (`isConnected`, root-node containment) → skip if any container contains it OR composedPath pierces a shadow boundary to include it → if target is NOT loosely-focusable and tabIndex!==-1, preventDefault so an open Menu closes but a click onto ANOTHER Menu's button still opens that one → invoke callback.
**Invariant:** the judged target for mouse is the pointerDOWN element (a panel that unmounts on pointerdown won't swallow the close decision); capture-phase registration defeats intermediate stopPropagation; touch uses the LIVE end target with the 30px scroll-cancel; mobile devices skip the pointer pair entirely (touch handlers own it).
**Probe:** deterministic checks executed against source semantics: threshold comparison uses raw absolute deltas on BOTH axes; composedPath fallback `?.()[0] || target`. Direct tests: dialog.test.tsx Mouse-interactions suites + menu/popover outside-click suites exercise nested dismissal and preventDefault cooperation.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "useOutsideClick", name_pattern: "^useOutsideClick$", limit: 5 });
```

## Verdict
Adopt the three-channel design (pointer pair / touch threshold / iframe blur) and the defaultPrevented veto verbatim; adapt the container resolution to your overlay registry; omit the Loose-focusable preventDefault nuance ONLY if you don't need click-onto-another-trigger opens-both behavior. Caveat: no standalone unit test file; contract pinned transitively via component suites.
