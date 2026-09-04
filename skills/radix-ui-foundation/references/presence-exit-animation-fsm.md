<!-- capsule-v2 -->
# Presence exit-animation FSM — how do you keep a component mounted through its CSS exit animation without flashes or update loops?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How does Presence decide to unmount instantly vs wait for an animation, and how does it survive animationcancel, React 18 flash, and unstable consumer refs?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/presence/src/presence.tsx:usePresence` (:29-187), machine wiring (:36-48), END handler (:106-167), `useStableComposedRefs` (:215-245); `packages/react/presence/src/use-state-machine.tsx:useStateMachine` (:12-20).
**Signature:** `usePresence(present) → { isPresent, ref }`; `Presence` accepts element child or render-prop `({present}) => element`.
**Data Shape:** states `mounted / unmountSuspended / unmounted`; events `MOUNT / UNMOUNT / ANIMATION_OUT / ANIMATION_END`; refs track prevPresent, prevAnimationName, mountAnimationName; stylesRef caches the live CSSStyleDeclaration from the ref callback.

### Decisive source
```ts
} else if (currentAnimationName === 'none' || styles?.display === 'none') {
  send('UNMOUNT');                    // no exit animation ⇒ instant
} else {
  const isAnimating = prevAnimationName !== currentAnimationName;
  if (wasPresent && isAnimating) send('ANIMATION_OUT');
  else send('UNMOUNT');
}
...
const isCurrentAnimation = currentAnimationName.includes(CSS.escape(event.animationName));
if (event.target === node && isCurrentAnimation) {
  send('ANIMATION_END');
  if (!prevPresentRef.current) {
    const currentFillMode = node.style.animationFillMode;
    node.style.animationFillMode = 'forwards';   // pin last keyframe …
    timeoutId = ownerWindow.setTimeout(() => {   // … restore after unmount window
      if (node.style.animationFillMode === 'forwards') {
        node.style.animationFillMode = currentFillMode;
      }
    });
  }
}
node.addEventListener('animationcancel', handleAnimationEnd);
```

**Flow:** layout effect on present-change reads computed animation-name (captured eagerly in the ref callback while styles are clean — passive effects like react-remove-scroll dirty body styles later, #1634) → name change ⇒ exit animation started ⇒ suspend; `animationend` AND `animationcancel` share one handler gated by CSS.escape'd name comparison (cancel fires when a new animation interrupts the exit) → ANIMATION_END only for the CURRENT animation; render-prop children stay mounted by design (`forceMount = typeof children === 'function'`). Reducer machine ignores undefined transitions (`nextState ?? state`) so unknown events are no-ops.
**Invariant:** comparing animation NAMES (not events alone) is the mechanism because there is no `animationrun` event and `animationstart` fires after `animation-delay` expires; fill-mode must be restored via setTimeout (not rAF) or the visible-content flash returns (PR#1849); `useStableComposedRefs` never changes callback identity — React 19 detaches/re-attaches refs whose identity changes per commit, which would otherwise loop `setNode` into "Maximum update depth exceeded" (#3664).
**Probe:** direct tests `packages/react/presence/src/presence.test.tsx` — `does not loop when the child has a stable ref` (:10) and `…unstable callback ref that triggers a render on attach` (:25). Byte-exact anchors: `bash -c "cd $REFERENCE_ROOT/external/ui-radix-ui && grep -nF 'CSS.escape(event.animationName)' packages/react/presence/src/presence.tsx"` (:119) and `grep -cF 'unmountSuspended' packages/react/presence/src/presence.tsx"` (=4).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "usePresence ANIMATION_OUT unmountSuspended state machine", limit: 10 });
```

## Verdict
Adopt the FSM + name-delta + cancel-twin + fill-mode latch as one unit — they exist to cover each other's failure modes; adapt the style-read strategy only if your host has no sibling effects dirtying styles; omit getElementRef's DEV-warning dance only on React ≥19 production builds. Direct tests present upstream at this pin (presence.test.tsx).
