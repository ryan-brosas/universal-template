<!-- capsule-v2 -->
# FocusScope trap — how do you trap focus across portals without stealing it from tab/window switches, and what breaks nested overlays?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** What is the exact reclaim/bail/loop logic of a trapped focus scope, including the removed-focused-node case and the nested-scope pause protocol?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/focus-scope/src/focus-scope.tsx:FocusScope` (:57-239), trap effect (:101-163), mount/unmount autofocus effect (:165-203), `focusScopesStack` (:420-452), branch registry `useFocusScopeBranchRegistry`/`useFocusScopeBranch` (:284-307).
**Signature:** `<FocusScope loop? trapped? branches?: HTMLElement[] onMountAutoFocus? onUnmountAutoFocus?>`; module-singleton stack of `{paused, pause(), resume()}`.
**Data Shape:** `lastFocusedElementRef` remembers last in-scope focused node; tabbable candidates via TreeWalker filter (`node.tabIndex >= 0`, skip disabled/hidden/hidden-input); custom events `focusScope.autoFocusOnMount|OnUnmount` are cancelable.

### Decisive source
```ts
function handleFocusOut(event: FocusEvent) {
  if (focusScope.paused || !container) return;
  const relatedTarget = event.relatedTarget as HTMLElement | null;
  // A `focusout` with null relatedTarget: app/tab switch OR Chrome removing the
  // focused element. The browser keeps its own memory; fighting it pegs CPU.
  if (relatedTarget === null) return;
  if (!isTargetInScope(relatedTarget)) {
    focus(lastFocusedElementRef.current, { select: true });
  }
}
function handleMutations(mutations: MutationRecord[]) {
  const focusedElement = document.activeElement as HTMLElement | null;
  if (focusedElement !== document.body) return;
  for (const mutation of mutations) {
    if (mutation.removedNodes.length > 0) focus(container);
  }
}
```

**Flow:** mount → push scope on stack (pausing previous top) → dispatch cancelable AUTOFOCUS_ON_MOUNT; not prevented ⇒ focusFirst(tabbables minus `<A>` links) else focus container → trap handlers reclaim out-of-scope focus to `lastFocusedElementRef` (select:true so inputs re-select text); Tab edges wrap only when `loop`; unmount → inside `setTimeout(0)` dispatch cancelable AUTOFOCUS_ON_UNMOUNT then restore `previouslyFocusedElement ?? document.body` (React#17894 delay) and resume the new stack top. Portalled React-descendants register via branch context so the trap treats them as in-scope (#3423).
**Invariant:** null-relatedTarget MUST bail (both the tab-switch and Chrome-removed-node cases; refocusing a deleted element spins CPU to 100%); MutationObserver-driven container refocus fires ONLY when activeElement fell back to body; positive-tabIndex nodes are collected but their DOM order deliberately overrides tabIndex ordering (positive-tabIndex ordering "hinders accessibility").
**Probe:** direct tests `packages/react/focus-scope/src/focus-scope.test.tsx` (309L suite). Byte-exact anchors: `bash -c "cd $REFERENCE_ROOT/external/ui-radix-ui && grep -nF 'if (relatedTarget === null) return;' packages/react/focus-scope/src/focus-scope.tsx"` (:130) and `grep -nF \"item.tagName !== 'A'\" packages/react/focus-scope/src/focus-scope.tsx"` (:455 removeLinks).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "FocusScope trapped focusin focusout lastFocusedElementRef", limit: 10 });
```

## Verdict
Adopt the trap lattice verbatim — every guard here encodes a real browser bug; adapt the branch registry only if your portal layer differs; omit the legacy `isHidden` walk when all targets support `checkVisibility` (the code already prefers it). Upstream focus-scope.test.tsx provides direct coverage at this pin.
