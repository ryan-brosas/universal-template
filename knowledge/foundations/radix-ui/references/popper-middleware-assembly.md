<!-- capsule-v2 -->
# Popper middleware assembly — how is floating-ui configured so overlays position deterministically, hide when detached, and expose sizing CSS vars?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** Which floating-ui middlewares, in which order and with which options, produce radix's popper behavior?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/popper/src/popper.tsx:PopperContent` (:182-358), middleware array (:241-277), wrapper style (:306-332), custom `transformOrigin` middleware (:430-465), anchor registration in `PopperAnchor` (:93-144).
**Signature:** `<PopperContent side sideOffset align alignOffset arrowPadding avoidCollisions collisionBoundary collisionPadding sticky hideWhenDetached updatePositionStrategy onPlaced?>`.
**Data Shape:** `useFloating({strategy:'fixed', placement: side+('-'+align if ≠center), whileElementsMounted: autoUpdate(..., {animationFrame: strategy==='always'}), elements:{reference: context.anchor}, middleware:[...]})`; size.apply writes four CSS custom props; arrow measured via useSize (span wrapper because ResizeObserver misreports SVG boxes).

### Decisive source
```ts
middleware: [
  offset({ mainAxis: sideOffset + arrowHeight, alignmentAxis: alignOffset }),
  avoidCollisions && shift({
    mainAxis: true, crossAxis: false,
    limiter: sticky === Sticky.Partial ? limitShift() : undefined,
    ...detectOverflowOptions,
  }),
  avoidCollisions && flip({ ...detectOverflowOptions }),
  size({ ...detectOverflowOptions, apply: ({elements, rects}) => {
    elements.floating.style.setProperty('--radix-popper-available-width', `${availableWidth}px`);
    ...
  }}),
  arrow && floatingUIarrow({ element: arrow, padding: arrowPadding }),
  transformOrigin({ arrowWidth, arrowHeight }),
  hideWhenDetached && hide({
    strategy: 'referenceHidden', ...detectOverflowOptions,
    // no explicit boundary ⇒ undefined = Floating-UI clipping ancestors,
    // so an occluded submenu hides once its anchor scrolls away (#3237)
    boundary: hasExplicitBoundaries ? detectOverflowOptions.boundary : undefined,
  }),
],
```

**Flow:** anchor set from a COMMIT-PHASE callback ref (effects count toward the nested-update limit — many poppers mounting at once crashed with "Maximum update depth exceeded", #3858) → placement resolved → placedSide/Align derived by splitting the placement string → content wrapped in a positioning div whose style starts at `translate(0, -200%)` (off-page) until `isPositioned`, then switches to floatingStyles.transform → animations suppressed (`animation:'none'`) until positioned so they never fire from the wrong side → custom transformOrigin middleware computes x/y from arrow center (falling back to percentage alignment when the arrow can't center). Placement state is mirrored to context for data-side/data-align attributes.
**Invariant:** middleware ORDER is load-bearing (offset before shift/flip; size before consumers of its CSS vars; hide last); `strategy:'fixed'` default exists to dodge focus-scroll jumps; altBoundary only flips on when explicit boundaries are given; zIndex must be COPIED from computed content styles onto the wrapper or stacking-context children escape it.
**Probe:** direct tests `packages/react/popper/src/popper.test.tsx` (295L). Byte-exact anchors: `bash -c "cd $REFERENCE_ROOT/external/ui-radix-ui && grep -nF \"strategy: 'fixed',\" packages/react/popper/src/popper.tsx"` (:229) and `grep -nF 'boundary: hasExplicitBoundaries ? detectOverflowOptions.boundary : undefined,' packages/react/popper/src/popper.tsx"` (:275).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "PopperContent middleware shift flip hide referenceHidden", limit: 10 });
```

## Verdict
Adopt the ladder order + fixed strategy + off-page-until-positioned dance verbatim; adapt option values and CSS var names to your design system; omit the hide-middleware ancestor fallback only if your host has no scrollable clipping containers (record it). Direct popper.test.tsx coverage upstream at this pin.
